from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    Compra,
    DetallePedido,
    Gasto,
    Insumo,
    Pago,
    Pedido,
    Producto,
    Venta,
)

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


def ventas_por_dia(db: Session, desde: date, hasta: date) -> list[dict]:
    dia = func.date(Venta.fecha_venta)
    filas = (
        db.query(
            dia.label("fecha"),
            func.coalesce(func.sum(Venta.total), 0).label("total"),
            func.count(Venta.id_venta).label("num_ventas"),
        )
        .filter(
            dia >= desde,
            dia <= hasta,
            Venta.estado_venta == "Completada",
        )
        .group_by(dia)
        .order_by(dia)
        .all()
    )
    return [
        {
            "fecha": f.fecha,
            "total": Decimal(str(f.total)),
            "num_ventas": f.num_ventas,
        }
        for f in filas
    ]


def gastos_por_dia(db: Session, desde: date, hasta: date) -> list[dict]:
    dia = func.date(Gasto.fecha_gasto)
    filas = (
        db.query(
            dia.label("fecha"),
            func.coalesce(func.sum(Gasto.monto), 0).label("total"),
            func.count(Gasto.id_gasto).label("num_gastos"),
        )
        .filter(
            dia >= desde,
            dia <= hasta,
        )
        .group_by(dia)
        .order_by(dia)
        .all()
    )
    return [
        {
            "fecha": f.fecha,
            "total": Decimal(str(f.total)),
            "num_gastos": f.num_gastos,
        }
        for f in filas
    ]


def top_productos(
    db: Session, desde: date, hasta: date, limite: int = 10
) -> list[dict]:
    dia = func.date(Venta.fecha_venta)
    filas = (
        db.query(
            Producto.id_producto.label("id_producto"),
            Producto.nombre_producto.label("nombre"),
            func.sum(DetallePedido.cantidad).label("cantidad"),
            func.sum(DetallePedido.subtotal).label("importe"),
        )
        .select_from(Venta)
        .join(Pedido, Pedido.id_pedido == Venta.id_pedido)
        .join(DetallePedido, DetallePedido.id_pedido == Pedido.id_pedido)
        .join(Producto, Producto.id_producto == DetallePedido.id_producto)
        .filter(
            dia >= desde,
            dia <= hasta,
            Venta.estado_venta == "Completada",
        )
        .group_by(Producto.id_producto, Producto.nombre_producto)
        .order_by(func.sum(DetallePedido.cantidad).desc())
        .limit(limite)
        .all()
    )
    return [
        {
            "id_producto": f.id_producto,
            "nombre": f.nombre,
            "cantidad": int(f.cantidad),
            "importe": Decimal(str(f.importe)),
        }
        for f in filas
    ]


def detalle_ventas(
    db: Session,
    desde: date,
    hasta: date,
    id_usuario: int | None = None,
    id_metodo: int | None = None,
) -> list[dict]:
    query = db.query(Venta).filter(
        func.date(Venta.fecha_venta) >= desde,
        func.date(Venta.fecha_venta) <= hasta,
        Venta.estado_venta == "Completada",
    )
    if id_usuario is not None:
        # id_usuario = mesero que tomó el pedido (Pedido.id_usuario), no el
        # cajero que cobró (Venta.id_usuario).
        query = query.join(Pedido, Pedido.id_pedido == Venta.id_pedido).filter(
            Pedido.id_usuario == id_usuario
        )
    if id_metodo is not None:
        # `.any(...)` evita duplicar filas: una venta con pago dividido que
        # incluya el método buscado aparece una sola vez.
        query = query.filter(Venta.pagos.any(Pago.id_metodo_pago == id_metodo))
    ventas = query.order_by(Venta.fecha_venta).all()
    out = []
    for v in ventas:
        pedido = db.get(Pedido, v.id_pedido)
        metodos = ", ".join(sorted({p.metodo.nombre_metodo for p in v.pagos}))
        out.append(
            {
                "folio": v.ticket.folio if v.ticket else "",
                "fecha": v.fecha_venta,
                "mesa": pedido.mesa.numero_mesa if pedido and pedido.mesa else None,
                "total": v.total,
                "metodos": metodos,
            }
        )
    return out


def detalle_gastos(
    db: Session,
    desde: date,
    hasta: date,
    id_usuario: int | None = None,
    id_categoria: int | None = None,
) -> list[dict]:
    query = db.query(Gasto).filter(
        func.date(Gasto.fecha_gasto) >= desde,
        func.date(Gasto.fecha_gasto) <= hasta,
    )
    if id_usuario is not None:
        query = query.filter(Gasto.id_usuario == id_usuario)
    if id_categoria is not None:
        query = query.filter(Gasto.id_categoria_gasto == id_categoria)
    gastos = query.order_by(Gasto.fecha_gasto).all()
    return [
        {
            "fecha": g.fecha_gasto,
            "categoria": g.categoria.nombre_categoria,
            "concepto": g.concepto,
            "monto": g.monto,
        }
        for g in gastos
    ]


def comparativo(db: Session, desde: date, hasta: date) -> dict:
    n = (hasta - desde).days + 1
    ant_hasta = desde - timedelta(days=1)
    ant_desde = desde - timedelta(days=n)
    actual = resumen(db, desde, hasta)
    anterior = resumen(db, ant_desde, ant_hasta)

    def _delta(a, b) -> float | None:
        b = Decimal(str(b))
        if b == 0:
            return None
        return float(round((Decimal(str(a)) - b) / b * 100, 1))

    claves = ("total_vendido", "total_gastos", "utilidad_estimada", "num_ventas")
    deltas = {k: _delta(actual[k], anterior[k]) for k in claves}
    return {"actual": actual, "anterior": anterior, "deltas": deltas}


def inventario_niveles(db: Session, solo_bajo_minimo: bool = False) -> list[dict]:
    query = db.query(Insumo)
    if solo_bajo_minimo:
        query = query.filter(Insumo.stock_actual < Insumo.stock_minimo)
    out = []
    for i in query.all():
        smin = float(i.stock_minimo)
        sact = float(i.stock_actual)
        if smin > 0:
            pct = min(100, round(sact / (2 * smin) * 100))
        else:
            pct = 100 if sact > 0 else 0
        out.append(
            {
                "nombre": i.nombre_insumo,
                "unidad": i.unidad.abreviatura,
                "stock_actual": i.stock_actual,
                "stock_minimo": i.stock_minimo,
                "nivel_pct": pct,
                "bajo_minimo": i.stock_actual < i.stock_minimo,
            }
        )
    out.sort(key=lambda x: x["nivel_pct"])
    return out


def _bucket_expr(fecha_col, agrupar: str):
    """Expresión SQL de agrupación por columna de fecha, según granularidad."""
    if agrupar == "mes":
        return func.date(func.date_trunc("month", fecha_col))
    if agrupar == "semana":
        return func.date(func.date_trunc("week", fecha_col))
    return func.date(fecha_col)


def _periodo_str(bucket: date, agrupar: str) -> str:
    if agrupar == "mes":
        return bucket.strftime("%Y-%m")
    return bucket.isoformat()


def estado_resultados(
    db: Session, desde: date, hasta: date, agrupar: str
) -> list[dict]:
    """Estado de resultados agrupado por bucket (día/semana/mes): ventas,
    gastos, compras y utilidad, fusionando las 3 fuentes por periodo."""
    bucket_venta = _bucket_expr(Venta.fecha_venta, agrupar)
    bucket_gasto = _bucket_expr(Gasto.fecha_gasto, agrupar)
    bucket_compra = _bucket_expr(Compra.fecha_compra, agrupar)

    ventas_rows = (
        db.query(
            bucket_venta.label("bucket"),
            func.coalesce(func.sum(Venta.total), 0).label("total"),
        )
        .filter(
            func.date(Venta.fecha_venta) >= desde,
            func.date(Venta.fecha_venta) <= hasta,
            Venta.estado_venta == "Completada",
        )
        .group_by(bucket_venta)
        .all()
    )
    gastos_rows = (
        db.query(
            bucket_gasto.label("bucket"),
            func.coalesce(func.sum(Gasto.monto), 0).label("total"),
        )
        .filter(
            func.date(Gasto.fecha_gasto) >= desde,
            func.date(Gasto.fecha_gasto) <= hasta,
        )
        .group_by(bucket_gasto)
        .all()
    )
    compras_rows = (
        db.query(
            bucket_compra.label("bucket"),
            func.coalesce(func.sum(Compra.total), 0).label("total"),
        )
        .filter(
            func.date(Compra.fecha_compra) >= desde,
            func.date(Compra.fecha_compra) <= hasta,
        )
        .group_by(bucket_compra)
        .all()
    )

    acumulado: dict[date, dict[str, Decimal]] = {}

    def _acumula(rows, campo):
        for r in rows:
            fila = acumulado.setdefault(
                r.bucket, {"ventas": _CERO, "gastos": _CERO, "compras": _CERO}
            )
            fila[campo] = fila[campo] + Decimal(str(r.total))

    _acumula(ventas_rows, "ventas")
    _acumula(gastos_rows, "gastos")
    _acumula(compras_rows, "compras")

    out = []
    for bucket in sorted(acumulado):
        fila = acumulado[bucket]
        out.append(
            {
                "periodo": _periodo_str(bucket, agrupar),
                "ventas": fila["ventas"],
                "gastos": fila["gastos"],
                "compras": fila["compras"],
                "utilidad": fila["ventas"] - fila["gastos"] - fila["compras"],
            }
        )
    return out
