"""Modelo del informe de mercado: resumen HTML de las watchlists listo para email.

Reúne las cotizaciones de ``market_data`` para los símbolos registrados en
``watchlists`` y las renderiza con una plantilla Jinja2 pensada para clientes
de correo (tablas y estilos en línea). Como el resto de modelos, no depende
de Flask: usa Jinja2 directamente, así que puede llamarse desde un script o
una tarea programada sin contexto de aplicación.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.models import market_data
from app.models.email import send_email
from app.models.market_data import Quote
from app.models.watchlists import WATCHLISTS, Symbol, Watchlist, get_watchlist

TOP_MOVERS = 3

_env = Environment(
    loader=FileSystemLoader(Path(__file__).resolve().parent.parent / "views" / "emails"),
    autoescape=select_autoescape(["html"]),
)


@dataclass(slots=True)
class ReportRow:
    """Una fila del informe: el símbolo de la watchlist y su cotización."""

    symbol: Symbol
    quote: Quote


@dataclass(slots=True)
class ReportSection:
    watchlist: Watchlist
    rows: list[ReportRow]


@dataclass(slots=True)
class MarketReport:
    """Informe listo para enviar: asunto + cuerpo HTML."""

    subject: str
    html: str
    generated_at: datetime
    sections: list[ReportSection]


def _fetch_quote(ticker: str) -> Quote:
    """Como ``market_data.get_quote`` pero sin romper el informe si un símbolo falla."""
    try:
        return market_data.get_quote(ticker)
    except Exception:
        return Quote(symbol=ticker, name=ticker, price=None, previous_close=None, change=None, change_percent=None)


def _resolve_watchlists(slugs: list[str] | None) -> list[Watchlist]:
    if not slugs:
        return list(WATCHLISTS)
    watchlists = []
    for slug in slugs:
        watchlist = get_watchlist(slug)
        if watchlist is None:
            raise ValueError(f"Watchlist no encontrada: {slug}")
        watchlists.append(watchlist)
    return watchlists


def _format_price(value: float | None) -> str:
    return "—" if value is None else f"{value:,.2f}"


def _format_change(value: float | None, suffix: str = "") -> str:
    return "—" if value is None else f"{value:+,.2f}{suffix}"


_env.filters["price"] = _format_price
_env.filters["change"] = _format_change


def build_market_report(slugs: list[str] | None = None) -> MarketReport:
    """Obtiene las cotizaciones y construye el informe HTML.

    ``slugs`` limita el informe a esas watchlists (por defecto, todas). Lanza
    ``ValueError`` si algún slug no existe.
    """
    watchlists = _resolve_watchlists(slugs)
    generated_at = datetime.now(timezone.utc)

    sections = [
        ReportSection(
            watchlist=watchlist,
            rows=[ReportRow(symbol=s, quote=_fetch_quote(s.ticker)) for s in watchlist.symbols],
        )
        for watchlist in watchlists
    ]

    # Un mismo ticker puede aparecer en varias watchlists (p. ej. SONY): en el
    # resumen global se cuenta una sola vez.
    unique_rows = list({row.symbol.ticker: row for section in sections for row in section.rows}.values())
    with_change = sorted(
        (row for row in unique_rows if row.quote.change_percent is not None),
        key=lambda row: row.quote.change_percent,
        reverse=True,
    )
    gainers = [row for row in with_change if row.quote.change_percent > 0][:TOP_MOVERS]
    losers = [row for row in reversed(with_change) if row.quote.change_percent < 0][:TOP_MOVERS]

    summary = {
        "total": len(unique_rows),
        "up": sum(1 for row in with_change if row.quote.change_percent > 0),
        "down": sum(1 for row in with_change if row.quote.change_percent < 0),
        "unavailable": len(unique_rows) - len(with_change),
    }

    subject = f"Informe de mercado · {generated_at:%d/%m/%Y}"
    html = _env.get_template("market_report.html").render(
        subject=subject,
        generated_at=generated_at,
        sections=sections,
        summary=summary,
        gainers=gainers,
        losers=losers,
    )
    return MarketReport(subject=subject, html=html, generated_at=generated_at, sections=sections)


def send_market_report(to: str | list[str], slugs: list[str] | None = None) -> str:
    """Construye el informe y lo envía por email. Devuelve el id del envío de Resend."""
    report = build_market_report(slugs)
    return send_email(to, report.subject, report.html)
