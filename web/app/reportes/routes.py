from datetime import date

from flask import Blueprint, Response, render_template, request
from flask_login import login_required

from app.dashboard.routes import rango_preset
from app.services import api_client, api_gateway, export

bp = Blueprint("reportes", __name__)


def _reporte(tipo, filas):
    """Normaliza un reporte a (titulo, headers, rows, total_row) con tipos nativos.

    Las filas llevan tipos reales (date, float, int|None) para que el XLSX use
    celdas numéricas/fecha (SUM/orden/filtro en Excel). La capa de presentación
    (HTML/PDF) las formatea con _fmt_rows; así una sola definición de columnas
    sirve para preview/PDF/XLSX.
    """
    if tipo == "gastos":
        headers = ["Fecha", "Categoría", "Concepto", "Monto"]
        rows = [
            [date.fromisoformat(f["fecha"][:10]), f["categoria"], f["concepto"], float(f["monto"])]
            for f in filas
        ]
        total = sum(float(f["monto"]) for f in filas)
        return "Reporte de Gastos", headers, rows, ["Total", "", "", total]
    headers = ["Folio", "Fecha", "Mesa", "Total", "Métodos"]
    rows = [
        [
            f["folio"],
            date.fromisoformat(f["fecha"][:10]),
            f["mesa"],
            float(f["total"]),
            f["metodos"],
        ]
        for f in filas
    ]
    total = sum(float(f["total"]) for f in filas)
    return "Reporte de Ventas", headers, rows, ["Total", "", "", total, ""]


def _fmt_cell(v):
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _fmt_rows(rows):
    return [[_fmt_cell(c) for c in r] for r in rows]


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
    formato = request.args.get("formato")
    if formato in ("xlsx", "pdf"):
        base = f"reporte-{tipo}-{desde}_{hasta}"
        if formato == "xlsx":
            data = export.to_xlsx(titulo, headers, rows, total_row)
            ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            fname = f"{base}.xlsx"
        else:
            html = render_template(
                "reportes/print.html",
                titulo=titulo, headers=headers,
                rows=_fmt_rows(rows), total_row=_fmt_rows([total_row])[0],
                desde=desde, hasta=hasta,
            )
            data = export.to_pdf(html)
            ctype = "application/pdf"
            fname = f"{base}.pdf"
        return Response(
            data,
            mimetype=ctype,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    return render_template(
        "reportes/index.html",
        tipo=tipo, titulo=titulo, headers=headers,
        rows=_fmt_rows(rows), total_row=_fmt_rows([total_row])[0],
        preset=preset, desde=desde, hasta=hasta,
    )
