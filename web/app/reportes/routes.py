from flask import Blueprint, render_template, request
from flask_login import login_required

from app.dashboard.routes import rango_preset
from app.services import api_client, api_gateway

bp = Blueprint("reportes", __name__)


def _reporte(tipo, filas):
    """Normaliza un reporte a (titulo, headers, rows, total_row) para preview/export."""
    if tipo == "gastos":
        headers = ["Fecha", "Categoría", "Concepto", "Monto"]
        rows = [
            [f["fecha"][:10], f["categoria"], f["concepto"], f"{float(f['monto']):.2f}"]
            for f in filas
        ]
        total = sum(float(f["monto"]) for f in filas)
        return "Reporte de Gastos", headers, rows, ["Total", "", "", f"{total:.2f}"]
    headers = ["Folio", "Fecha", "Mesa", "Total", "Métodos"]
    rows = [
        [
            f["folio"],
            f["fecha"][:10],
            "" if f["mesa"] is None else str(f["mesa"]),
            f"{float(f['total']):.2f}",
            f["metodos"],
        ]
        for f in filas
    ]
    total = sum(float(f["total"]) for f in filas)
    return "Reporte de Ventas", headers, rows, ["Total", "", "", f"{total:.2f}", ""]


@bp.route("/reportes")
@login_required
def index():
    tipo = "gastos" if request.args.get("tipo") == "gastos" else "ventas"
    preset = request.args.get("preset", "mes")
    desde, hasta = rango_preset(
        preset, request.args.get("desde"), request.args.get("hasta")
    )
    if tipo == "gastos":
        filas = api_gateway.call(api_client.get_reporte_gastos, desde, hasta)
    else:
        filas = api_gateway.call(api_client.get_reporte_ventas, desde, hasta)
    titulo, headers, rows, total_row = _reporte(tipo, filas)
    return render_template(
        "reportes/index.html",
        tipo=tipo, titulo=titulo, headers=headers, rows=rows, total_row=total_row,
        preset=preset, desde=desde, hasta=hasta,
    )
