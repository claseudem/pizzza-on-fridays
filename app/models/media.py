"""Modelo de medios: imágenes optimizadas servidas desde Cloudinary.

Toda la interacción con el SDK de ``cloudinary`` vive aquí, siguiendo el
mismo patrón que ``market_data.py`` (Yahoo Finance) y ``email.py`` (Resend).
Las URLs se generan con ``f_auto,q_auto``: Cloudinary elige el formato
(AVIF/WebP/JPEG) y la calidad óptimos para cada navegador, y ``w_<ancho>``
sirve la resolución justa para cada pantalla vía ``srcset``.

Si ``CLOUDINARY_URL`` no está configurada, las funciones devuelven ``None``
y quien las llama usa la copia local de ``static/img/informes``.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import cloudinary
import cloudinary.uploader
from cloudinary import CloudinaryImage

from config import Config

# Carpeta en Cloudinary y copia local de las imágenes de la página de Informes
# (la copia local es la fuente de la subida y el respaldo sin Cloudinary).
PUBLIC_ID_PREFIX = "market-dashboard/informes"
LOCAL_IMAGE_DIR = Path(__file__).resolve().parent.parent / "static" / "img" / "informes"
INFORMES_IMAGES = ("charts", "stats", "sports")

RESPONSIVE_WIDTHS = (640, 1280, 1920)
DEFAULT_WIDTH = 1280


class MediaError(RuntimeError):
    """Error de configuración o de la API de Cloudinary."""


@dataclass(frozen=True, slots=True)
class ResponsiveImage:
    src: str
    srcset: str


def is_configured() -> bool:
    return bool(Config.CLOUDINARY_URL)


def _configure() -> None:
    """Aplica ``CLOUDINARY_URL`` (cloudinary://<api_key>:<api_secret>@<cloud_name>) al SDK."""
    url = urlparse(Config.CLOUDINARY_URL)
    if url.scheme != "cloudinary" or not url.hostname:
        raise MediaError("CLOUDINARY_URL debe tener la forma cloudinary://<api_key>:<api_secret>@<cloud_name>")
    cloudinary.config(
        cloud_name=url.hostname,
        api_key=url.username,
        api_secret=url.password,
        secure=True,
    )


def image_url(public_id: str, width: int = DEFAULT_WIDTH) -> str:
    """URL de entrega con compresión automática (f_auto,q_auto) y ancho máximo ``width``.

    ``c_limit`` reduce la imagen a ese ancho pero nunca la amplía.
    """
    _configure()
    return CloudinaryImage(public_id).build_url(
        fetch_format="auto",
        quality="auto",
        width=width,
        crop="limit",
    )


def informes_image(name: str) -> ResponsiveImage | None:
    """Imagen responsive (``src`` + ``srcset``) de la página de Informes, o ``None`` sin Cloudinary."""
    if not is_configured():
        return None
    public_id = f"{PUBLIC_ID_PREFIX}/{name}"
    return ResponsiveImage(
        src=image_url(public_id, DEFAULT_WIDTH),
        srcset=", ".join(f"{image_url(public_id, w)} {w}w" for w in RESPONSIVE_WIDTHS),
    )


def upload_informes_images() -> list[str]:
    """Sube (o reemplaza) las imágenes locales de Informes a Cloudinary y devuelve sus URLs."""
    if not is_configured():
        raise MediaError("Falta CLOUDINARY_URL en el .env")
    _configure()

    urls = []
    for name in INFORMES_IMAGES:
        try:
            result = cloudinary.uploader.upload(
                str(LOCAL_IMAGE_DIR / f"{name}.jpg"),
                public_id=f"{PUBLIC_ID_PREFIX}/{name}",
                overwrite=True,
                invalidate=True,
                resource_type="image",
            )
        except Exception as exc:  # la excepción concreta la define el SDK de cloudinary
            raise MediaError(f"No se pudo subir {name}.jpg: {exc}") from exc
        urls.append(result["secure_url"])
    return urls
