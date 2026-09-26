"""Application factory.

Este es el punto de ensamblaje del patrón MVC: crea la app Flask, le aplica
la configuración y registra los controladores (blueprints). Los modelos y
las vistas no se importan aquí directamente, solo a través de los
controladores, para mantener las capas desacopladas.
"""
from __future__ import annotations

from flask import Flask

from config import Config


def create_app(config_class: type[Config] = Config) -> Flask:
    app = Flask(
        __name__,
        template_folder="views",  # nombramos "views" (no "templates") para reflejar el MVC
        static_folder="static",
    )
    app.config.from_object(config_class)

    register_blueprints(app)
    register_context_processors(app)

    return app


def register_blueprints(app: Flask) -> None:
    """Registra cada controlador.

    Añadir una nueva app de primer nivel (otra entrada en el sidebar) implica:
    registrar su entrada en ``app.models.apps.APPS`` y su blueprint aquí.
    """
    from app.controllers.api import bp as api_bp
    from app.controllers.graficas import bp as graficas_bp
    from app.controllers.home import bp as home_bp
    from app.controllers.quant_stats import bp as quant_stats_bp
    from app.controllers.varianza import bp as varianza_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(graficas_bp)
    app.register_blueprint(varianza_bp)
    app.register_blueprint(quant_stats_bp)
    app.register_blueprint(api_bp)


def register_context_processors(app: Flask) -> None:
    from app.models.apps import APPS

    @app.context_processor
    def inject_apps() -> dict:
        # Disponible en todas las plantillas (el sidebar se incluye en base.html).
        return {"apps": APPS}
