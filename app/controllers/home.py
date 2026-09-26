"""Controlador: raíz del sitio. Muestra la landing page pública."""
from __future__ import annotations

from flask import Blueprint, render_template

bp = Blueprint("home", __name__)


@bp.get("/")
def index():
    return render_template("landing.html")
