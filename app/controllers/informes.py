"""Controlador de la app "Informes": vista previa y envío por email del informe de activos."""
from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, render_template, url_for

from app.models import media
from app.models.apps import get_app
from app.models.watchlists import WATCHLISTS

bp = Blueprint("informes", __name__, url_prefix="/informes")

# Escenas de fondo de la página. Cada una se anima en un <canvas>; si existe
# ``static/video/informes-<escena>.webm`` y/o ``.mp4`` se usa ese video en
# bucle y el canvas queda como respaldo por si el navegador no lo reproduce.
FX_SCENES = ("charts", "stats", "sports")
# WebM (VP9) primero: lo reproducen todos los Chromium/Electron y Firefox,
# incluso sin códecs propietarios. MP4 (H.264) queda para Safari.
FX_VIDEO_FORMATS = (("webm", "video/webm"), ("mp4", "video/mp4"))


def _fx_videos() -> dict[str, list[tuple[str, str]]]:
    video_dir = Path(current_app.static_folder) / "video"
    videos: dict[str, list[tuple[str, str]]] = {}
    for scene in FX_SCENES:
        sources = [
            (url_for("static", filename=f"video/informes-{scene}.{ext}"), mime)
            for ext, mime in FX_VIDEO_FORMATS
            if (video_dir / f"informes-{scene}.{ext}").is_file()
        ]
        if sources:
            videos[scene] = sources
    return videos


def _fx_images() -> dict[str, dict[str, str | None]]:
    """Imagen de cada escena: desde Cloudinary (f_auto,q_auto + srcset) o, sin
    configurar, la copia local."""
    images: dict[str, dict[str, str | None]] = {}
    for scene in FX_SCENES:
        remote = media.informes_image(scene)
        if remote is not None:
            images[scene] = {"src": remote.src, "srcset": remote.srcset}
        elif (media.LOCAL_IMAGE_DIR / f"{scene}.jpg").is_file():
            images[scene] = {"src": url_for("static", filename=f"img/informes/{scene}.jpg"), "srcset": None}
    return images


@bp.get("/")
def index():
    return render_template(
        "informes.html",
        active_app=get_app("informes"),
        watchlists=WATCHLISTS,
        fx_videos=_fx_videos(),
        fx_images=_fx_images(),
    )
