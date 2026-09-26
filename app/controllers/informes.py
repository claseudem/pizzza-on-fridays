"""Controlador de la app "Informes": vista previa y envío por email del informe de activos."""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, render_template, url_for

from app.models.apps import get_app
from app.models.watchlists import WATCHLISTS

bp = Blueprint("informes", __name__, url_prefix="/informes")

# Escenas de fondo de la página. Cada una se anima en un <canvas>; si existe
# ``static/video/informes-<escena>.mp4`` se usa ese video en bucle en su lugar.
FX_SCENES = ("charts", "stats", "sports")


def _fx_videos() -> dict[str, str]:
    video_dir = Path(current_app.static_folder) / "video"
    return {
        scene: url_for("static", filename=f"video/informes-{scene}.mp4")
        for scene in FX_SCENES
        if (video_dir / f"informes-{scene}.mp4").is_file()
    }


@bp.get("/")
def index():
    return render_template(
        "informes.html",
        active_app=get_app("informes"),
        watchlists=WATCHLISTS,
        fx_videos=_fx_videos(),
    )
