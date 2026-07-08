"""Tests del generador de datos demo (`app.db.seed_demo`).

Usa el fixture transaccional `db` (rollback automático). Llama SIEMPRE a las
funciones que reciben `db` -nunca a `run()`-, que abriría otra sesión real.
"""

from datetime import date, timedelta
from decimal import Decimal

from app.db.seed_demo import seed_demo, seed_transacciones
from app.models import Venta
from app.services import reporte_service

# Días reducidos para que el fixture transaccional corra rápido; conserva el
# guard de idempotencia, la variación fin de semana y el espectro de inventario.
DIAS_TEST = 30


def test_seed_demo_enciende_los_reportes(db):
    resultado = seed_demo(db, dias=DIAS_TEST)

    assert resultado["ventas"] > 0
    assert resultado["gastos"] > 0
    assert resultado["compras"] > 0
    assert resultado["insumos"] >= 10
    assert resultado["omitido"] is False

    hoy = date.today()
    desde = hoy - timedelta(days=DIAS_TEST - 1)

    resumen = reporte_service.resumen(db, desde, hoy)
    assert resumen["total_vendido"] > 0
    assert resumen["num_ventas"] > 0
    assert resumen["ticket_promedio"] > 0
    assert resumen["total_gastos"] > 0
    assert resumen["total_compras"] > 0

    serie = reporte_service.ventas_por_dia(db, desde, hoy)
    assert len(serie) > 1
    assert all(f["num_ventas"] > 0 for f in serie)
    assert all(f["total"] > 0 for f in serie)

    top = reporte_service.top_productos(db, desde, hoy)
    assert len(top) > 0
    cantidades = [p["cantidad"] for p in top]
    assert cantidades == sorted(cantidades, reverse=True)

    detalle_v = reporte_service.detalle_ventas(db, desde, hoy)
    assert len(detalle_v) > 0
    assert all(d["folio"] for d in detalle_v)

    detalle_g = reporte_service.detalle_gastos(db, desde, hoy)
    assert len(detalle_g) > 0

    comp_desde = hoy - timedelta(days=13)
    comparativo = reporte_service.comparativo(db, comp_desde, hoy)
    assert comparativo["actual"]["num_ventas"] > 0
    assert comparativo["anterior"]["num_ventas"] > 0
    assert any(v is not None for v in comparativo["deltas"].values())

    niveles = reporte_service.inventario_niveles(db)
    assert len(niveles) > 0
    assert any(n["bajo_minimo"] for n in niveles)
    assert any(n["nivel_pct"] >= 90 for n in niveles)


def test_seed_transacciones_es_idempotente(db):
    seed_demo(db, dias=DIAS_TEST)
    total_ventas_1 = db.query(Venta).count()

    resultado_2 = seed_transacciones(db, dias=DIAS_TEST)

    assert resultado_2["ventas"] == 0
    assert resultado_2["omitido"] is True
    assert db.query(Venta).count() == total_ventas_1


def test_pagos_de_cada_venta_suman_el_total(db):
    seed_demo(db, dias=DIAS_TEST)
    ventas = db.query(Venta).limit(50).all()

    assert ventas
    for v in ventas:
        suma_pagos = sum((p.monto for p in v.pagos), Decimal("0"))
        assert suma_pagos == v.total


def test_seed_demo_es_determinista_en_conteo_de_ventas(db):
    """Con random.seed(42) fijo, dos corridas sobre el mismo estado inicial
    (mismo `hoy`, mismos catálogos) generan el mismo número de ventas."""
    nested_1 = db.begin_nested()
    resultado_1 = seed_demo(db, dias=DIAS_TEST)
    conteo_1 = resultado_1["ventas"]
    nested_1.rollback()

    nested_2 = db.begin_nested()
    resultado_2 = seed_demo(db, dias=DIAS_TEST)
    conteo_2 = resultado_2["ventas"]
    nested_2.rollback()

    assert conteo_1 > 0
    assert conteo_1 == conteo_2
