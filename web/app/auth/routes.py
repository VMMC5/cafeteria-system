from flask import (
    Blueprint, flash, redirect, render_template, request, session, url_for
)
from flask_login import login_required, login_user, logout_user

from app.auth import WebUser
from app.services import api_client
from app.services.api_client import ApiError

bp = Blueprint("auth", __name__)

SUPPORT_URL = "mailto:soporte@cafeteria.com"


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        correo = (request.form.get("correo") or "").strip()
        password = request.form.get("password") or ""
        if not correo or not password:
            flash("Correo y contraseña son obligatorios.", "error")
            return render_template("auth/login.html", support_url=SUPPORT_URL), 400
        try:
            tokens = api_client.login(correo, password)
        except ApiError:
            flash("Credenciales incorrectas.", "error")
            return render_template("auth/login.html", support_url=SUPPORT_URL), 401
        me = api_client.get_me(tokens["access_token"])
        if me["rol"]["nombre_rol"] != "Administrador":
            flash("Acceso exclusivo para administradores.", "error")
            return render_template("auth/login.html", support_url=SUPPORT_URL), 403
        session["access"] = tokens["access_token"]
        session["refresh"] = tokens["refresh_token"]
        session["user"] = {
            "id": me["id_usuario"],
            "nombre": me["nombre"],
            "correo": me["correo"],
            "rol": me["rol"]["nombre_rol"],
        }
        login_user(
            WebUser(me["id_usuario"], me["nombre"], me["correo"], me["rol"]["nombre_rol"])
        )
        return redirect(url_for("usuarios.listar"))
    return render_template("auth/login.html", support_url=SUPPORT_URL)


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
