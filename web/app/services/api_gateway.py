from flask import session
from flask_login import logout_user

from app.services import api_client
from app.services.api_client import ApiError


class ReloginRequired(Exception):
    """Se agotó el refresh; hay que volver a iniciar sesión."""


def call(fn, *args):
    """Llama fn(access, *args) inyectando el token; ante 401 refresca una vez."""
    access = session.get("access")
    try:
        return fn(access, *args)
    except ApiError as e:
        if e.status_code != 401:
            raise
        try:
            tokens = api_client.refresh(session.get("refresh"))
        except ApiError:
            logout_user()
            session.clear()
            raise ReloginRequired()
        session["access"] = tokens["access_token"]
        session["refresh"] = tokens["refresh_token"]
        return fn(tokens["access_token"], *args)
