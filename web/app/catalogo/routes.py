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


def _payload_categoria(form):
    return {
        "nombre_categoria": form["nombre_categoria"].strip(),
        "descripcion": (form.get("descripcion") or "").strip() or None,
    }


@bp.route("/categorias")
@login_required
def categorias():
    items = api_gateway.call(api_client.list_categorias)
    return render_template("catalogo/categorias_list.html", categorias=items)


@bp.route("/categorias/nueva")
@login_required
def categoria_nueva():
    return render_template("catalogo/categorias_form.html", categoria=None, form={})


@bp.route("/categorias", methods=["POST"])
@login_required
def categoria_crear():
    try:
        api_gateway.call(api_client.create_categoria, _payload_categoria(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        return (
            render_template("catalogo/categorias_form.html", categoria=None, form=request.form),
            e.status_code,
        )
    flash("Categoría creada.", "info")
    return redirect(url_for("catalogo.categorias"))


@bp.route("/categorias/<int:id_categoria>/editar")
@login_required
def categoria_editar(id_categoria):
    categoria = api_gateway.call(api_client.get_categoria, id_categoria)
    return render_template("catalogo/categorias_form.html", categoria=categoria, form=categoria)


@bp.route("/categorias/<int:id_categoria>", methods=["POST"])
@login_required
def categoria_actualizar(id_categoria):
    try:
        api_gateway.call(api_client.update_categoria, id_categoria, _payload_categoria(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        categoria = api_gateway.call(api_client.get_categoria, id_categoria)
        return (
            render_template("catalogo/categorias_form.html", categoria=categoria, form=request.form),
            e.status_code,
        )
    flash("Categoría actualizada.", "info")
    return redirect(url_for("catalogo.categorias"))


@bp.route("/categorias/<int:id_categoria>/eliminar", methods=["POST"])
@login_required
def categoria_eliminar(id_categoria):
    try:
        api_gateway.call(api_client.delete_categoria, id_categoria)
        flash("Categoría eliminada.", "info")
    except ApiError as e:
        flash(e.detail, "error")
    return redirect(url_for("catalogo.categorias"))


def _payload_mesa(form):
    data = {
        "numero_mesa": int(form["numero_mesa"]),
        "capacidad": int(form["capacidad"]),
        "ubicacion": (form.get("ubicacion") or "").strip() or None,
    }
    # El form de una mesa Ocupada no manda estado: nunca se pisa desde el panel.
    if form.get("estado"):
        data["estado"] = form["estado"]
    return data


@bp.route("/mesas")
@login_required
def mesas():
    items = api_gateway.call(api_client.list_mesas)
    return render_template("catalogo/mesas_list.html", mesas=items)


@bp.route("/mesas/nueva")
@login_required
def mesa_nueva():
    return render_template("catalogo/mesas_form.html", mesa=None, form={})


@bp.route("/mesas", methods=["POST"])
@login_required
def mesa_crear():
    try:
        api_gateway.call(api_client.create_mesa, _payload_mesa(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        return (
            render_template("catalogo/mesas_form.html", mesa=None, form=request.form),
            e.status_code,
        )
    flash("Mesa creada.", "info")
    return redirect(url_for("catalogo.mesas"))


@bp.route("/mesas/<int:id_mesa>/editar")
@login_required
def mesa_editar(id_mesa):
    mesa = api_gateway.call(api_client.get_mesa, id_mesa)
    return render_template("catalogo/mesas_form.html", mesa=mesa, form=mesa)


@bp.route("/mesas/<int:id_mesa>", methods=["POST"])
@login_required
def mesa_actualizar(id_mesa):
    try:
        api_gateway.call(api_client.update_mesa, id_mesa, _payload_mesa(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        mesa = api_gateway.call(api_client.get_mesa, id_mesa)
        return (
            render_template("catalogo/mesas_form.html", mesa=mesa, form=request.form),
            e.status_code,
        )
    flash("Mesa actualizada.", "info")
    return redirect(url_for("catalogo.mesas"))


@bp.route("/mesas/<int:id_mesa>/eliminar", methods=["POST"])
@login_required
def mesa_eliminar(id_mesa):
    try:
        api_gateway.call(api_client.delete_mesa, id_mesa)
        flash("Mesa eliminada.", "info")
    except ApiError as e:
        flash(e.detail, "error")
    return redirect(url_for("catalogo.mesas"))
