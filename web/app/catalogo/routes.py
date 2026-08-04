from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services import api_client, api_gateway
from app.services.api_client import ApiError

bp = Blueprint("catalogo", __name__, url_prefix="/catalogo")


def _payload_producto(form):
    return {
        "nombre_producto": form["nombre_producto"].strip(),
        "descripcion": (form.get("descripcion") or "").strip() or None,
        "id_categoria": int(form["id_categoria"]),
        "precio_venta": form["precio_venta"],
        "disponible": form.get("disponible") == "on",
    }


@bp.route("")
@login_required
def index():
    return redirect(url_for("catalogo.productos"))


@bp.route("/productos")
@login_required
def productos():
    cat = request.args.get("categoria") or ""
    disp = request.args.get("disponible") or ""
    id_categoria = int(cat) if cat else None
    disponible = None if disp == "" else disp == "1"
    items = api_gateway.call(api_client.list_productos, id_categoria, disponible)
    categorias = api_gateway.call(api_client.list_categorias)
    return render_template(
        "catalogo/productos_list.html",
        productos=items, categorias=categorias, categoria=cat, disponible=disp,
    )


@bp.route("/productos/nuevo")
@login_required
def producto_nuevo():
    categorias = api_gateway.call(api_client.list_categorias)
    return render_template(
        "catalogo/productos_form.html",
        categorias=categorias, producto=None, form={"disponible": True},
    )


@bp.route("/productos", methods=["POST"])
@login_required
def producto_crear():
    try:
        api_gateway.call(api_client.create_producto, _payload_producto(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        categorias = api_gateway.call(api_client.list_categorias)
        return (
            render_template(
                "catalogo/productos_form.html",
                categorias=categorias, producto=None, form=request.form,
            ),
            e.status_code,
        )
    flash("Producto creado.", "info")
    return redirect(url_for("catalogo.productos"))


@bp.route("/productos/<int:id_producto>/editar")
@login_required
def producto_editar(id_producto):
    producto = api_gateway.call(api_client.get_producto, id_producto)
    categorias = api_gateway.call(api_client.list_categorias)
    return render_template(
        "catalogo/productos_form.html",
        categorias=categorias, producto=producto, form=producto,
    )


@bp.route("/productos/<int:id_producto>", methods=["POST"])
@login_required
def producto_actualizar(id_producto):
    try:
        api_gateway.call(
            api_client.update_producto, id_producto, _payload_producto(request.form)
        )
    except ApiError as e:
        flash(e.detail, "error")
        producto = api_gateway.call(api_client.get_producto, id_producto)
        categorias = api_gateway.call(api_client.list_categorias)
        return (
            render_template(
                "catalogo/productos_form.html",
                categorias=categorias, producto=producto, form=request.form,
            ),
            e.status_code,
        )
    flash("Producto actualizado.", "info")
    return redirect(url_for("catalogo.productos"))


@bp.route("/productos/<int:id_producto>/toggle", methods=["POST"])
@login_required
def producto_toggle(id_producto):
    disponible = request.form.get("disponible") == "1"
    try:
        api_gateway.call(api_client.update_producto, id_producto, {"disponible": disponible})
        flash("Producto actualizado.", "info")
    except ApiError as e:
        flash(e.detail, "error")
    return redirect(url_for("catalogo.productos"))
