from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Compra, Gasto, Venta

_CERO = Decimal("0.00")


def rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hoy = date.today()
    return (desde or hoy, hasta or hoy)


def _suma(db: Session, columna, fecha_col, desde: date, hasta: date, *filtros):
    q = db.query(func.coalesce(func.sum(columna), 0)).filter(
        func.date(fecha_col) >= desde, func.date(fecha_col) <= hasta
    )
    for f in filtros:
        q = q.filter(f)
    return Decimal(str(q.scalar() or 0))


def resumen(db: Session, desde: date, hasta: date) -> dict:
    completada = Venta.estado_venta == "Completada"
    total_vendido = _suma(
        db, Venta.total, Venta.fecha_venta, desde, hasta, completada
    )
    num_ventas = (
        db.query(func.count(Venta.id_venta))
        .filter(
            func.date(Venta.fecha_venta) >= desde,
            func.date(Venta.fecha_venta) <= hasta,
            completada,
        )
        .scalar()
    )
    total_gastos = _suma(db, Gasto.monto, Gasto.fecha_gasto, desde, hasta)
    total_compras = _suma(db, Compra.total, Compra.fecha_compra, desde, hasta)
    ticket = (
        (total_vendido / num_ventas).quantize(Decimal("0.01"))
        if num_ventas
        else _CERO
    )
    return {
        "total_vendido": total_vendido,
        "num_ventas": num_ventas,
        "ticket_promedio": ticket,
        "total_gastos": total_gastos,
        "total_compras": total_compras,
        "utilidad_estimada": total_vendido - total_gastos - total_compras,
    }
