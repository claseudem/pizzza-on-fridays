"""Controlador: raíz del sitio. Landing page de bienvenida."""
from __future__ import annotations

from flask import Blueprint, render_template

from app.models.apps import get_app

bp = Blueprint("home", __name__)


@bp.get("/")
def index():
    return render_template(
        "landing.html",
        graficas_app=get_app("graficas"),
        varianza_app=get_app("analisis-varianza"),
    )
