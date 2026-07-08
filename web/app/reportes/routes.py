from datetime import date

from flask import Blueprint, Response, render_template, request
from flask_login import login_required

from app.dashboard.routes import rango_preset
from app.services import api_client, api_gateway, export

bp = Blueprint("reportes", __name__)

TIPOS = ("ventas", "gastos", "inventario", "estado_resultados")


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
    if tipo == "inventario":
        headers = ["Insumo", "Unidad", "Stock actual", "Stock mínimo", "Nivel %", "Bajo mínimo"]
        rows = [
            [
                f["nombre"],
                f["unidad"],
                float(f["stock_actual"]),
                float(f["stock_minimo"]),
                int(f["nivel_pct"]),
                "Sí" if f["bajo_minimo"] else "No",
            ]
            for f in filas
        ]
        return "Reporte de Inventario", headers, rows, None
    if tipo == "estado_resultados":
        headers = ["Periodo", "Ventas", "Gastos", "Compras", "Utilidad"]
        rows = [
            [
                f["periodo"],
                float(f["ventas"]),
                float(f["gastos"]),
                float(f["compras"]),
                float(f["utilidad"]),
            ]
            for f in filas
        ]
        total = [
            "Total",
            sum(r[1] for r in rows),
            sum(r[2] for r in rows),
            sum(r[3] for r in rows),
            sum(r[4] for r in rows),
        ]
        return "Estado de Resultados", headers, rows, total
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


def _fmt_total(total_row):
    return _fmt_rows([total_row])[0] if total_row is not None else None


def _int_arg(name):
    v = request.args.get(name)
    if v in (None, ""):
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _nombre_usuario(u):
    partes = [u.get("nombre"), u.get("apellido_paterno"), u.get("apellido_materno")]
    return " ".join(p for p in partes if p)


@bp.route("/reportes")
@login_required
def index():
    tipo = request.args.get("tipo")
    if tipo not in TIPOS:
        tipo = "ventas"
    preset = request.args.get("preset", "mes")
    desde, hasta = rango_preset(
        preset, request.args.get("desde"), request.args.get("hasta")
    )
    id_usuario = _int_arg("id_usuario")
    id_metodo = _int_arg("id_metodo")
    id_categoria = _int_arg("id_categoria")
    agrupar = request.args.get("agrupar", "dia")
    solo_bajo_minimo = request.args.get("solo_bajo_minimo") is not None

    if tipo == "gastos":
        filas = api_gateway.call(
            api_client.get_reporte_gastos, desde, hasta, id_usuario, id_categoria
        )
    elif tipo == "inventario":
        filas = api_gateway.call(api_client.get_inventario_niveles, solo_bajo_minimo)
    elif tipo == "estado_resultados":
        filas = api_gateway.call(
            api_client.get_estado_resultados, desde, hasta, agrupar
        )
    else:
        filas = api_gateway.call(
            api_client.get_reporte_ventas, desde, hasta, id_usuario, id_metodo
        )
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
                rows=_fmt_rows(rows), total_row=_fmt_total(total_row),
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

    usuarios_raw = api_gateway.call(api_client.list_usuarios)
    usuarios = [
        {"id_usuario": u["id_usuario"], "nombre": _nombre_usuario(u)}
        for u in usuarios_raw
    ]
    metodos = api_gateway.call(api_client.get_metodos_pago)
    categorias = api_gateway.call(api_client.get_gastos_categorias)

    serie_er = None
    if tipo == "estado_resultados":
        serie_er = [
            {"periodo": r[0], "ventas": r[1], "gastos": r[2], "utilidad": r[4]}
            for r in rows
        ]

    return render_template(
        "reportes/index.html",
        tipo=tipo, titulo=titulo, headers=headers,
        rows=_fmt_rows(rows), total_row=_fmt_total(total_row),
        preset=preset, desde=desde, hasta=hasta,
        id_usuario=id_usuario, id_metodo=id_metodo, id_categoria=id_categoria,
        agrupar=agrupar, solo_bajo_minimo=solo_bajo_minimo,
        usuarios=usuarios, metodos=metodos, categorias=categorias,
        serie_er=serie_er,
    )
