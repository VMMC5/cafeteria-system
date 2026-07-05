from flask import (
    Blueprint, flash, redirect, render_template, request, url_for
)
from flask_login import login_required

from app.services import api_client, api_gateway
from app.services.api_client import ApiError

bp = Blueprint("usuarios", __name__)


def _payload(form, incluir_password=True):
    data = {
        "nombre": form["nombre"].strip(),
        "apellido_paterno": form["apellido_paterno"].strip(),
        "apellido_materno": (form.get("apellido_materno") or "").strip() or None,
        "correo": form["correo"].strip(),
        "nombre_usuario": form["nombre_usuario"].strip(),
        "id_rol": int(form["id_rol"]),
    }
    if incluir_password and form.get("password"):
        data["password"] = form["password"]
    return data


@bp.route("/usuarios")
@login_required
def listar():
    q = request.args.get("q")
    usuarios = api_gateway.call(api_client.list_usuarios, q)
    return render_template("usuarios/list.html", usuarios=usuarios, q=q or "")


@bp.route("/usuarios/nuevo")
@login_required
def nuevo():
    roles = api_gateway.call(api_client.list_roles)
    return render_template("usuarios/form.html", roles=roles, usuario=None, form={})


@bp.route("/usuarios", methods=["POST"])
@login_required
def crear():
    try:
        api_gateway.call(api_client.create_usuario, _payload(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        roles = api_gateway.call(api_client.list_roles)
        return (
            render_template("usuarios/form.html", roles=roles, usuario=None, form=request.form),
            e.status_code,
        )
    flash("Usuario creado.", "info")
    return redirect(url_for("usuarios.listar"))


@bp.route("/usuarios/<int:id_usuario>/editar")
@login_required
def editar(id_usuario):
    usuario = api_gateway.call(api_client.get_usuario, id_usuario)
    roles = api_gateway.call(api_client.list_roles)
    return render_template("usuarios/form.html", roles=roles, usuario=usuario, form=usuario)


@bp.route("/usuarios/<int:id_usuario>", methods=["POST"])
@login_required
def actualizar(id_usuario):
    try:
        api_gateway.call(api_client.update_usuario, id_usuario, _payload(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        roles = api_gateway.call(api_client.list_roles)
        usuario = api_gateway.call(api_client.get_usuario, id_usuario)
        return (
            render_template("usuarios/form.html", roles=roles, usuario=usuario, form=request.form),
            e.status_code,
        )
    flash("Usuario actualizado.", "info")
    return redirect(url_for("usuarios.listar"))


@bp.route("/usuarios/<int:id_usuario>/desactivar", methods=["POST"])
@login_required
def desactivar(id_usuario):
    try:
        api_gateway.call(api_client.delete_usuario, id_usuario)
        flash("Usuario desactivado.", "info")
    except ApiError as e:
        flash(e.detail, "error")
    return redirect(url_for("usuarios.listar"))
