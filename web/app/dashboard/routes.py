from datetime import date, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.services import api_client, api_gateway

bp = Blueprint("dashboard", __name__)


def rango_preset(preset, desde, hasta):
    """Devuelve (desde, hasta) en ISO según el preset o el rango explícito."""
    hoy = date.today()
    if preset == "7dias":
        return (hoy - timedelta(days=6)).isoformat(), hoy.isoformat()
    if preset == "mes":
        return hoy.replace(day=1).isoformat(), hoy.isoformat()
    if preset == "rango" and desde and hasta:
        return desde, hasta
    return hoy.isoformat(), hoy.isoformat()  # "hoy" (default)


@bp.route("/dashboard")
@login_required
def index():
    preset = request.args.get("preset", "hoy")
    desde, hasta = rango_preset(
        preset, request.args.get("desde"), request.args.get("hasta")
    )
    resumen = api_gateway.call(api_client.get_reporte_resumen, desde, hasta)
    serie = api_gateway.call(api_client.get_ventas_por_dia, desde, hasta)
    top = api_gateway.call(api_client.get_top_productos, desde, hasta)
    return render_template(
        "dashboard/index.html",
        resumen=resumen, serie=serie, top=top,
        preset=preset, desde=desde, hasta=hasta,
    )
