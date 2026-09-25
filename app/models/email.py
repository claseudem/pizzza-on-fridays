"""Modelo de envío de emails: integración con la API de Resend.

Toda la interacción con ``resend`` vive aquí, siguiendo el mismo patrón que
``market_data.py`` para Yahoo Finance: los controladores nunca llaman al
SDK directamente, piden el envío a través de la función de este módulo.
"""
from __future__ import annotations

import resend

from config import Config


class EmailError(RuntimeError):
    """Error al enviar un email a través de Resend."""


def send_email(to: str | list[str], subject: str, html: str, *, from_email: str | None = None) -> str:
    """Envía un email con Resend y devuelve el id del envío.

    Requiere ``RESEND_API_KEY`` en el .env. Lanza ``EmailError`` si falta la
    clave o si la API de Resend devuelve un error.
    """
    if not Config.RESEND_API_KEY:
        raise EmailError("Falta RESEND_API_KEY en el .env")

    resend.api_key = Config.RESEND_API_KEY

    try:
        response = resend.Emails.send(
            {
                "from": from_email or Config.RESEND_FROM_EMAIL,
                "to": [to] if isinstance(to, str) else to,
                "subject": subject,
                "html": html,
            }
        )
    except Exception as exc:  # la excepción concreta la define el SDK de resend
        raise EmailError(str(exc)) from exc

    return response["id"]
