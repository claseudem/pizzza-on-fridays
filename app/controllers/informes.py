"""Controlador de la app "Informes": vista previa y envío por email del informe de activos."""
from __future__ import annotations

from flask import Blueprint, render_template

from app.models.apps import get_app
from app.models.watchlists import WATCHLISTS

bp = Blueprint("informes", __name__, url_prefix="/informes")


@bp.get("/")
def index():
    return render_template("informes.html", active_app=get_app("informes"), watchlists=WATCHLISTS)
