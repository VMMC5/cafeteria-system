from flask import Blueprint, render_template, request
from flask_login import login_required

from app.services import api_client, api_gateway

bp = Blueprint("usuarios", __name__)


@bp.route("/usuarios")
@login_required
def listar():
    q = request.args.get("q")
    usuarios = api_gateway.call(api_client.list_usuarios, q)
    return render_template("usuarios/list.html", usuarios=usuarios, q=q or "")


# Stubs para que url_for resuelva en list.html; se completan en Task 4.
@bp.route("/usuarios/nuevo")
@login_required
def nuevo():
    return "", 501


@bp.route("/usuarios/<int:id_usuario>/editar")
@login_required
def editar(id_usuario):
    return "", 501


@bp.route("/usuarios/<int:id_usuario>/desactivar", methods=["POST"])
@login_required
def desactivar(id_usuario):
    return "", 501
