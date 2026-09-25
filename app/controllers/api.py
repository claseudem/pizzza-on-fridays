"""Controlador: API JSON (y de imágenes) que consume el JavaScript del panel."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify, request

from app.models import analysis, market_data, quant
from app.models.watchlists import get_watchlist

bp = Blueprint("api", __name__, url_prefix="/api")

ALLOWED_INTERVALS = {"1m", "5m", "15m", "30m", "1h", "1d", "1wk", "1mo"}
ALLOWED_RANGES = {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"}
MAX_VOLATILITY_TICKERS = 6
QUANT_PERIODS = {"1y", "2y", "5y", "max"}


@bp.get("/quote/<ticker>")
def quote(ticker: str):
    return jsonify(market_data.get_quote(ticker).to_dict())


@bp.get("/candles/<ticker>")
def candles(ticker: str):
    range_ = request.args.get("range", "6mo")
    interval = request.args.get("interval", "1d")
    if range_ not in ALLOWED_RANGES or interval not in ALLOWED_INTERVALS:
        return jsonify({"error": "range o interval inválidos"}), 400
    return jsonify(market_data.get_candles(ticker, range_, interval))


@bp.get("/watchlist/<slug>/quotes")
def watchlist_quotes(slug: str):
    """Precios de todos los símbolos de una watchlist, para pintar el sidebar."""
    watchlist = get_watchlist(slug)
    if watchlist is None:
        return jsonify({"error": "watchlist no encontrada"}), 404
    quotes = {s.ticker: market_data.get_quote(s.ticker).to_dict() for s in watchlist.symbols}
    return jsonify(quotes)


@bp.get("/volatility-chart")
def volatility_chart():
    """Histograma (PNG) de la volatilidad mensual de uno o varios tickers.

    ?tickers=AAPL,MSFT,GOOG&period=5y
    """
    tickers = [t.strip().upper() for t in request.args.get("tickers", "").split(",") if t.strip()]
    period = request.args.get("period", "5y")

    if not tickers:
        return jsonify({"error": "Indica al menos un ticker"}), 400
    if len(tickers) > MAX_VOLATILITY_TICKERS:
        return jsonify({"error": f"Máximo {MAX_VOLATILITY_TICKERS} tickers a la vez"}), 400
    if period not in ALLOWED_RANGES:
        return jsonify({"error": "period inválido"}), 400

    png_bytes = analysis.render_volatility_histograms(tickers, period)
    return Response(png_bytes, mimetype="image/png")


@bp.get("/quant/<ticker>/drawdown.png")
def quant_drawdown(ticker: str):
    """Serie de drawdown (PNG) calculada con quantstats. ?period=2y"""
    period = request.args.get("period", "2y")
    if period not in QUANT_PERIODS:
        return jsonify({"error": "period inválido"}), 400
    return Response(quant.render_drawdown_chart(ticker.upper(), period), mimetype="image/png")


@bp.get("/quant/<ticker>/monthly-heatmap.png")
def quant_monthly_heatmap(ticker: str):
    """Heatmap (PNG) de retornos mensuales calculados con quantstats. ?period=2y"""
    period = request.args.get("period", "2y")
    if period not in QUANT_PERIODS:
        return jsonify({"error": "period inválido"}), 400
    return Response(quant.render_monthly_heatmap(ticker.upper(), period), mimetype="image/png")


@bp.get("/quant/<ticker>/earnings.png")
def quant_earnings(ticker: str):
    """Comparación (PNG) de los últimos reportes de resultados. ?count=4"""
    count = request.args.get("count", 4, type=int)
    if count is None or not 2 <= count <= 8:
        return jsonify({"error": "count debe estar entre 2 y 8"}), 400
    return Response(quant.render_earnings_chart(ticker.upper(), count), mimetype="image/png")
