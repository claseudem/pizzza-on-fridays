"""Registro de "apps" de primer nivel del sidebar.

Este es el nivel de extensión más alto del panel: cada ``App`` es una
sección independiente (por ejemplo "Gráficas" o "Análisis de Varianza"),
con su propio icono, su propio blueprint/rutas y, opcionalmente, su propia
navegación anidada en el sidebar (ver ``kind``).

Para añadir una nueva app:

1. Añade una entrada aquí con un ``endpoint`` (el ``blueprint.vista`` de
   Flask que sirve como página principal de esa app).
2. Crea el blueprint correspondiente en ``app/controllers`` y regístralo
   en ``app/__init__.py``.
3. Si la app necesita su propia navegación anidada en el sidebar (como las
   watchlists de "Gráficas"), añade un nuevo valor de ``kind`` y su bloque
   correspondiente en ``app/views/partials/sidebar.html``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

AppKind = Literal["watchlists", "blank"]


@dataclass(frozen=True, slots=True)
class App:
    slug: str
    name: str
    icon: str
    endpoint: str
    kind: AppKind = "blank"


APPS: tuple[App, ...] = (
    App(slug="graficas", name="Gráficas", icon="📈", endpoint="graficas.index", kind="watchlists"),
    App(slug="analisis-varianza", name="Análisis de Varianza", icon="🧮", endpoint="varianza.index", kind="blank"),
    App(slug="analisis-uec", name="Análisis UEC", icon="☢️", endpoint="uec.index", kind="blank"),
    App(slug="informes", name="Informes", icon="📨", endpoint="informes.index", kind="blank"),
)


def default_app() -> App:
    return APPS[0]


def get_app(slug: str) -> App | None:
    return next((a for a in APPS if a.slug == slug), None)
