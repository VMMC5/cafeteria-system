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


# (label, key, up_is_good|None, es_money, es_accent)
_KPI_DEFS = [
    ("Total vendido", "total_vendido", True, True, False),
    ("# Ventas", "num_ventas", True, False, False),
    ("Ticket promedio", "ticket_promedio", None, True, False),
    ("Gastos", "total_gastos", False, True, False),
    ("Compras", "total_compras", None, True, False),
    ("Utilidad estimada", "utilidad_estimada", True, True, True),
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
    preset = request.args.get("preset", "hoy")
    desde, hasta = rango_preset(
        preset, request.args.get("desde"), request.args.get("hasta")
    )
    comp = api_gateway.call(api_client.get_comparativo, desde, hasta)
    serie = api_gateway.call(api_client.get_ventas_por_dia, desde, hasta)
    top = api_gateway.call(api_client.get_top_productos, desde, hasta)
    inventario = api_gateway.call(api_client.get_inventario_niveles)
    return render_template(
        "dashboard/index.html",
        kpis=_kpis(comp), serie=serie, top=top, inventario=inventario,
        preset=preset, desde=desde, hasta=hasta,
    )
