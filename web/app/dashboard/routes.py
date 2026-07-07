from datetime import date, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.services import api_client, api_gateway

bp = Blueprint("dashboard", __name__)


def _restar_meses(fecha, meses):
    """Retrocede `meses` meses naturales desde `fecha`, día 1 del mes destino.

    Aritmética de mes/año pura (no timedelta): evita el error de "180 días"
    que no equivale a 6 meses naturales y que además rompe en el cambio de
    año (p.ej. retroceder desde enero/febrero debe bajar el año).
    """
    total_meses = fecha.month - 1 - meses
    anio = fecha.year + total_meses // 12
    mes = total_meses % 12 + 1
    return date(anio, mes, 1)


def rango_preset(preset, desde, hasta):
    """Devuelve (desde, hasta) en ISO según el preset o el rango explícito."""
    hoy = date.today()
    if preset == "hoy":
        return hoy.isoformat(), hoy.isoformat()
    if preset == "7dias":
        return (hoy - timedelta(days=6)).isoformat(), hoy.isoformat()
    if preset == "6meses":
        return _restar_meses(hoy, 5).isoformat(), hoy.isoformat()
    if preset == "anio":
        return hoy.replace(month=1, day=1).isoformat(), hoy.isoformat()
    if preset == "rango" and desde and hasta:
        return desde, hasta
    # "mes" y cualquier preset desconocido/None -> mes (default sensato,
    # acorde al mockup: la UI arranca en "Mes", no en "Hoy").
    return hoy.replace(day=1).isoformat(), hoy.isoformat()


# (label, key, up_is_good|None, es_money, es_accent)
_KPI_DEFS = [
    ("Total vendido", "total_vendido", True, True, False),
    ("# Ventas", "num_ventas", True, False, False),
    ("Ticket promedio", "ticket_promedio", None, True, False),
    ("Gastos", "total_gastos", False, True, False),
    ("Compras", "total_compras", None, True, False),
    ("Utilidad estimada", "utilidad_estimada", True, True, True),
]


def _serie_ventas_vs_gastos(serie, gastos_serie):
    """Combina ventas y gastos por día en una serie alineada por fecha.

    Devuelve una lista ordenada por fecha con la unión de fechas presentes
    en ambas series; la fecha que falte en alguna de las dos se rellena
    con 0 en ese lado.
    """
    # La API serializa `total` como string (Decimal->JSON); coaccionar a float
    # antes de acumular (0 + "400.00" reventaría con TypeError).
    ventas_por_fecha = {}
    for p in serie:
        ventas_por_fecha[p["fecha"]] = (
            ventas_por_fecha.get(p["fecha"], 0) + float(p["total"])
        )
    gastos_por_fecha = {}
    for p in gastos_serie:
        gastos_por_fecha[p["fecha"]] = (
            gastos_por_fecha.get(p["fecha"], 0) + float(p["total"])
        )
    fechas = sorted(set(ventas_por_fecha) | set(gastos_por_fecha))
    return [
        {
            "fecha": f,
            "ventas": ventas_por_fecha.get(f, 0),
            "gastos": gastos_por_fecha.get(f, 0),
        }
        for f in fechas
    ]


def _bucketizar_mensual(serie_vg):
    """Agrupa una serie diaria alineada (ver `_serie_ventas_vs_gastos`) por mes.

    Suma `ventas`/`gastos` de cada día que cae en el mismo mes (`fecha[:7]`,
    formato "YYYY-MM") y devuelve la lista ordenada por mes ascendente.
    """
    acumulado = {}
    for p in serie_vg:
        mes = p["fecha"][:7]
        bucket = acumulado.setdefault(mes, {"ventas": 0, "gastos": 0})
        bucket["ventas"] += float(p["ventas"])
        bucket["gastos"] += float(p["gastos"])
    return [
        {"fecha": mes, "ventas": acumulado[mes]["ventas"], "gastos": acumulado[mes]["gastos"]}
        for mes in sorted(acumulado)
    ]


def _kpis(comp):
    actual, deltas = comp["actual"], comp["deltas"]
    tarjetas = []
    for label, key, up_good, money, accent in _KPI_DEFS:
        valor = f"${float(actual[key]):.2f}" if money else str(actual[key])
        delta = deltas.get(key) if up_good is not None else None
        if delta is None or delta == 0:
            flecha, color = "", "neutral"
        else:
            flecha = "▲" if delta > 0 else "▼"
            color = "up" if (delta > 0) == up_good else "down"
        tarjetas.append(
            {"label": label, "valor": valor, "delta": delta,
             "flecha": flecha, "color": color, "accent": accent}
        )
    return tarjetas


@bp.route("/dashboard")
@login_required
def index():
    preset = request.args.get("preset", "mes")
    desde, hasta = rango_preset(
        preset, request.args.get("desde"), request.args.get("hasta")
    )
    comp = api_gateway.call(api_client.get_comparativo, desde, hasta)
    serie = api_gateway.call(api_client.get_ventas_por_dia, desde, hasta)
    gastos_serie = api_gateway.call(api_client.get_gastos_por_dia, desde, hasta)
    top = api_gateway.call(api_client.get_top_productos, desde, hasta)
    inventario = api_gateway.call(api_client.get_inventario_niveles)
    # La tendencia (`serie`) siempre es diaria. La barra Ventas vs Gastos se
    # agrupa por mes cuando el periodo es largo (6meses/año); en Mes/Rango se
    # mantiene diaria.
    serie_vg = _serie_ventas_vs_gastos(serie, gastos_serie)
    if preset in ("6meses", "anio"):
        serie_vg = _bucketizar_mensual(serie_vg)
    return render_template(
        "dashboard/index.html",
        kpis=_kpis(comp), serie=serie, serie_vg=serie_vg, top=top,
        inventario=inventario, preset=preset, desde=desde, hasta=hasta,
    )
