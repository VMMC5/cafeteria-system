from flask import session
from flask_login import UserMixin


class WebUser(UserMixin):
    def __init__(self, id, nombre, correo, rol):
        self.id = str(id)
        self.nombre = nombre
        self.correo = correo
        self.rol = rol


def load_user_from_session():
    data = session.get("user")
    if not data:
        return None
    return WebUser(data["id"], data["nombre"], data["correo"], data["rol"])
