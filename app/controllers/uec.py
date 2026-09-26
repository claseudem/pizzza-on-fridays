"""Controlador de la app "Análisis UEC": métricas de quantstats, drawdown,
heatmap de retornos mensuales y comparación de los últimos earnings de
Uranium Energy Corp.

Las métricas y la tabla de earnings se renderizan en el servidor; las
gráficas son PNG que sirve la API (``/api/quant/<ticker>/...``).
"""
from __future__ import annotations

from flask import Blueprint, render_template, request

from app.models import quant
from app.models.apps import get_app

bp = Blueprint("uec", __name__, url_prefix="/analisis-uec")

TICKER = "UEC"
PERIODS = {"1y": "1 año", "2y": "2 años", "5y": "5 años", "max": "Todo"}
DEFAULT_PERIOD = "2y"
EARNINGS_COUNT = 4


@bp.get("/")
def index():
    period = request.args.get("period", DEFAULT_PERIOD)
    if period not in PERIODS:
        period = DEFAULT_PERIOD

    returns = quant.daily_returns(TICKER, period)
    return render_template(
        "uec.html",
        active_app=get_app("analisis-uec"),
        ticker=TICKER,
        period=period,
        periods=PERIODS,
        metrics=quant.performance_metrics(returns),
        earnings=quant.last_earnings(TICKER, EARNINGS_COUNT),
        earnings_count=EARNINGS_COUNT,
    )
