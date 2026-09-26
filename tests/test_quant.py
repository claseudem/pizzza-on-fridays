import datetime

import pytest

from app.models import quant

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _fake_candles(days=420):
    """~14 meses de precios diarios sintéticos (sin llamar a Yahoo Finance)."""
    candles = []
    price = 10.0
    date = datetime.datetime(2025, 1, 1)
    for i in range(days):
        date += datetime.timedelta(days=1)
        if date.weekday() >= 5:  # fin de semana: sin sesión
            continue
        price *= 1 + (0.02 if i % 3 else -0.03)
        candles.append(
            {"time": int(date.timestamp()), "open": price, "high": price, "low": price, "close": price, "volume": 1000}
        )
    return candles


def _ts(year, month, day):
    return int(datetime.datetime(year, month, day, 10).timestamp())


def _fake_earnings():
    """Del más reciente al más antiguo, como ``market_data.get_earnings``;
    el primero es un reporte futuro todavía sin EPS."""
    return [
        {"time": _ts(2099, 1, 1), "eps_estimate": -0.01, "eps_reported": None, "surprise_percent": None},
        {"time": _ts(2026, 1, 20), "eps_estimate": -0.02, "eps_reported": -0.01, "surprise_percent": 50.0},
        {"time": _ts(2025, 10, 20), "eps_estimate": -0.02, "eps_reported": -0.04, "surprise_percent": -100.0},
        {"time": _ts(2025, 7, 21), "eps_estimate": None, "eps_reported": -0.03, "surprise_percent": None},
        {"time": _ts(2025, 4, 21), "eps_estimate": -0.01, "eps_reported": -0.02, "surprise_percent": -100.0},
        {"time": _ts(2025, 1, 21), "eps_estimate": -0.01, "eps_reported": -0.05, "surprise_percent": -400.0},
    ]


@pytest.fixture()
def fake_market(monkeypatch):
    monkeypatch.setattr(quant.market_data, "get_candles", lambda *a, **k: _fake_candles())
    monkeypatch.setattr(quant.market_data, "get_earnings", lambda *a, **k: _fake_earnings())


def test_performance_metrics(fake_market):
    metrics = quant.performance_metrics(quant.daily_returns("FAKE"))
    assert metrics is not None
    assert metrics.annual_volatility > 0
    assert -1 <= metrics.max_drawdown < 0
    prices = quant.closing_prices("FAKE")
    assert metrics.cumulative_return == pytest.approx(prices.iloc[-1] / prices.iloc[0] - 1)


def test_performance_metrics_none_without_data():
    import pandas as pd

    assert quant.performance_metrics(pd.Series(dtype=float)) is None


def test_monthly_returns_table_blanks_months_outside_history(fake_market):
    table = quant.monthly_returns_table(quant.daily_returns("FAKE"))
    assert list(table.columns)[:1] == ["JAN"]
    # El histórico sintético termina en febrero de 2026: de marzo en adelante no hay datos.
    assert table.loc[2026].iloc[2:].isna().all()
    assert table.loc[2025].notna().all()


def test_last_earnings_are_the_last_published_in_chronological_order(fake_market):
    reports = quant.last_earnings("FAKE", 4)
    assert [r.date.month for r in reports] == [4, 7, 10, 1]  # sin el futuro ni el más antiguo
    assert reports[0].days_since_previous is None
    assert reports[1].days_since_previous == 91
    assert reports[-1].eps_change == pytest.approx(0.03)
    assert all(r.close is not None for r in reports)
    assert all(r.price_change_percent is not None for r in reports[1:])
    assert reports[-1].eps_beat is True
    assert reports[1].eps_beat is None  # sin estimado


@pytest.mark.parametrize(
    "render",
    [quant.render_drawdown_chart, quant.render_monthly_heatmap, quant.render_earnings_chart],
)
def test_charts_return_png_bytes(fake_market, render):
    assert render("FAKE").startswith(PNG_SIGNATURE)


@pytest.mark.parametrize(
    "render",
    [quant.render_drawdown_chart, quant.render_monthly_heatmap, quant.render_earnings_chart],
)
def test_charts_render_without_data(monkeypatch, render):
    monkeypatch.setattr(quant.market_data, "get_candles", lambda *a, **k: [])
    monkeypatch.setattr(quant.market_data, "get_earnings", lambda *a, **k: [])
    assert render("FAKE").startswith(PNG_SIGNATURE)
