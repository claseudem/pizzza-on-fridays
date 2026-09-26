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


@bp.get("/quant/<ticker>/plot/<slug>.png")
def quant_plot(ticker: str, slug: str):
    """Gráfica nativa (PNG) de ``quantstats.plots``. ?period=2y&benchmark=SPY&window=126"""
    ticker = quant.normalize_ticker(ticker)
    if ticker is None:
        return jsonify({"error": "ticker inválido"}), 400
    if quant.get_plot(slug) is None:
        return jsonify({"error": "gráfica desconocida"}), 404
    period = request.args.get("period", "2y")
    if period not in QUANT_PERIODS:
        return jsonify({"error": "period inválido"}), 400
    benchmark = request.args.get("benchmark") or None
    if benchmark is not None:
        benchmark = quant.normalize_ticker(benchmark)
        if benchmark is None:
            return jsonify({"error": "benchmark inválido"}), 400
    window = request.args.get("window", type=int)
    if "window" in request.args and window not in quant.ROLLING_WINDOWS:
        return jsonify({"error": "window inválido"}), 400
    png_bytes = quant.render_qs_plot(ticker, period, slug, benchmark=benchmark, window=window)
    return Response(png_bytes, mimetype="image/png")


@bp.get("/quant/<ticker>/montecarlo.png")
def quant_montecarlo(ticker: str):
    """Simulación Monte Carlo (PNG) de ``quantstats.stats.montecarlo``.
    ?period=2y&sims=1000&bust=-20&goal=50 (bust y goal en %)"""
    ticker = quant.normalize_ticker(ticker)
    if ticker is None:
        return jsonify({"error": "ticker inválido"}), 400
    period = request.args.get("period", "2y")
    if period not in QUANT_PERIODS:
        return jsonify({"error": "period inválido"}), 400
    sims = request.args.get("sims", quant.DEFAULT_MONTECARLO_SIMS, type=int)
    if sims not in quant.MONTECARLO_SIMS:
        return jsonify({"error": "sims inválido"}), 400
    bust = request.args.get("bust", quant.DEFAULT_BUST * 100, type=float)
    goal = request.args.get("goal", quant.DEFAULT_GOAL * 100, type=float)
    if bust is None or not -99 <= bust <= -1 or goal is None or not 1 <= goal <= 2000:
        return jsonify({"error": "bust debe estar entre -99 y -1 y goal entre 1 y 2000"}), 400
    png_bytes = quant.render_montecarlo_chart(ticker, period, sims, bust / 100, goal / 100)
    return Response(png_bytes, mimetype="image/png")
