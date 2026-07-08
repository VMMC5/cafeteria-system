"""Seed opt-in de datos ficticios (últimos N días) para encender los reportes
y estadísticas del panel web (resumen/KPIs, ventas-por-día, top-productos,
comparativo, detalle ventas/gastos, niveles de inventario).

NO forma parte del seed base y NO se ejecuta solo. Es idempotente: si ya hay
ventas, omite la generación de transacciones (los insumos se siembran aparte,
idempotentes por nombre).

Ejecutar:  docker compose exec api python -m app.db.seed_demo
"""

import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.db.seed import seed_base
from app.db.session import SessionLocal
from app.models import (
    CategoriaGasto,
    Compra,
    DetalleCompra,
    DetallePedido,
    EstadoPedido,
    Gasto,
    Insumo,
    Mesa,
    MetodoPago,
    Pago,
    Pedido,
    Producto,
    Proveedor,
    Ticket,
    UnidadMedida,
    Usuario,
    Venta,
)

DIAS_DEFAULT = 60

# (nombre, unidad, stock_actual, stock_minimo, costo_unitario)
# Espectro deliberado para `inventario_niveles`: varios bajo mínimo, algunos a
# nivel medio, y varios llenos/altos (nivel_pct >= 90).
INSUMOS_DEMO = [
    ("Café en grano", "Kilogramo", Decimal("2.0"), Decimal("5.0"), Decimal("180.00")),
    ("Leche entera", "Litro", Decimal("8.0"), Decimal("10.0"), Decimal("22.00")),
    ("Jamón", "Kilogramo", Decimal("3.0"), Decimal("5.0"), Decimal("120.00")),
    ("Azúcar", "Kilogramo", Decimal("12.0"), Decimal("10.0"), Decimal("18.00")),
    ("Pan de caja", "Pieza", Decimal("40.0"), Decimal("30.0"), Decimal("35.00")),
    ("Naranjas", "Kilogramo", Decimal("15.0"), Decimal("12.0"), Decimal("14.00")),
    ("Queso manchego", "Kilogramo", Decimal("8.0"), Decimal("4.0"), Decimal("150.00")),
    ("Lechuga", "Pieza", Decimal("30.0"), Decimal("15.0"), Decimal("12.00")),
    ("Pechuga de pollo", "Kilogramo", Decimal("18.0"), Decimal("8.0"), Decimal("95.00")),
    ("Chocolate en polvo", "Kilogramo", Decimal("12.0"), Decimal("5.0"), Decimal("140.00")),
    ("Harina", "Kilogramo", Decimal("22.0"), Decimal("10.0"), Decimal("16.00")),
    ("Servilletas", "Pieza", Decimal("500.0"), Decimal("200.0"), Decimal("0.50")),
]

CONCEPTOS_GASTO = {
    "Servicios": ["Luz", "Agua", "Internet", "Gas"],
    "Nómina": ["Pago quincenal personal", "Bono de desempeño"],
    "Mantenimiento": ["Reparación equipo de cocina", "Limpieza profunda", "Mantenimiento A/C"],
}


def seed_insumos(db) -> int:
    """Crea insumos demo con stock variado (bajo/medio/alto). Idempotente por
    nombre, igual que `seed_catalogo` con productos."""
    total = 0
    for nombre, unidad_nombre, stock_actual, stock_minimo, costo in INSUMOS_DEMO:
        existe = db.query(Insumo).filter(Insumo.nombre_insumo == nombre).first()
        if existe:
            continue
        unidad = (
            db.query(UnidadMedida)
            .filter(UnidadMedida.nombre_unidad == unidad_nombre)
            .one()
        )
        db.add(
            Insumo(
                id_unidad=unidad.id_unidad,
                nombre_insumo=nombre,
                descripcion=f"Insumo demo: {nombre}",
                stock_actual=stock_actual,
                stock_minimo=stock_minimo,
                costo_unitario=costo,
            )
        )
        total += 1
    db.flush()
    return total


def _fecha_en_dia(dia: date, hora_min: int, hora_max: int) -> datetime:
    hora = random.randint(hora_min, hora_max)
    minuto = random.randint(0, 59)
    return datetime.combine(dia, time(hora, minuto), tzinfo=timezone.utc)


def _generar_venta(
    db, dia: date, mesero, cajero, estado_entregado, mesas, productos, metodos, consecutivo: int
) -> None:
    mesa = random.choice(mesas)
    fecha_pedido = _fecha_en_dia(dia, 8, 20)

    pedido = Pedido(
        id_mesa=mesa.id_mesa,
        id_usuario=mesero.id_usuario,
        id_estado=estado_entregado.id_estado,
        fecha_pedido=fecha_pedido,
    )
    db.add(pedido)
    db.flush()

    n_lineas = random.randint(1, min(4, len(productos)))
    productos_venta = random.sample(productos, k=n_lineas)
    total_venta = Decimal("0.00")
    for prod in productos_venta:
        cantidad = random.randint(1, 3)
        precio = Decimal(str(prod.precio_venta))
        db.add(
            DetallePedido(
                id_pedido=pedido.id_pedido,
                id_producto=prod.id_producto,
                cantidad=cantidad,
                precio_unitario=precio,
            )
        )
        total_venta += cantidad * precio

    fecha_venta = fecha_pedido + timedelta(minutes=random.randint(5, 30))
    venta = Venta(
        id_pedido=pedido.id_pedido,
        id_usuario=cajero.id_usuario,
        fecha_venta=fecha_venta,
        total=total_venta,
        estado_venta="Completada",
    )
    db.add(venta)
    db.flush()

    folio = f"D-{consecutivo:06d}"
    db.add(Ticket(id_venta=venta.id_venta, folio=folio, fecha_emision=fecha_venta))

    r = random.random()
    if r < 0.15:
        # Pago dividido en 2 métodos: la suma exacta de los montos == total.
        nombres = random.sample(["Efectivo", "Tarjeta", "Transferencia"], 2)
        monto_1 = (total_venta / 2).quantize(Decimal("0.01"))
        monto_2 = total_venta - monto_1
        db.add(
            Pago(
                id_venta=venta.id_venta,
                id_metodo_pago=metodos[nombres[0]].id_metodo_pago,
                monto=monto_1,
                fecha_pago=fecha_venta,
            )
        )
        db.add(
            Pago(
                id_venta=venta.id_venta,
                id_metodo_pago=metodos[nombres[1]].id_metodo_pago,
                monto=monto_2,
                fecha_pago=fecha_venta,
            )
        )
    else:
        nombre_metodo = "Efectivo" if r < 0.15 + 0.55 else "Tarjeta"
        db.add(
            Pago(
                id_venta=venta.id_venta,
                id_metodo_pago=metodos[nombre_metodo].id_metodo_pago,
                monto=total_venta,
                fecha_pago=fecha_venta,
            )
        )


def seed_transacciones(db, dias: int = DIAS_DEFAULT) -> dict:
    """Genera ventas (con pedido/detalle/ticket/pagos), gastos y compras de los
    últimos `dias` días (hoy incluido). Idempotente: si ya hay ventas, omite
    por completo la generación (no duplica)."""
    if db.query(Venta).count() > 0:
        return {"ventas": 0, "gastos": 0, "compras": 0, "omitido": True}

    random.seed(42)

    mesero = db.query(Usuario).filter(Usuario.correo == "mesero@cafeteria.com").one()
    cajero = db.query(Usuario).filter(Usuario.correo == "cajero@cafeteria.com").one()
    estado_entregado = (
        db.query(EstadoPedido).filter(EstadoPedido.nombre_estado == "Entregado").one()
    )
    mesas = db.query(Mesa).all()
    productos = db.query(Producto).all()
    metodos = {m.nombre_metodo: m for m in db.query(MetodoPago).all()}
    insumos = db.query(Insumo).all()
    proveedores = db.query(Proveedor).all()
    categorias_gasto = db.query(CategoriaGasto).all()

    hoy = date.today()
    consecutivo = 0
    total_ventas = 0

    for offset in range(dias - 1, -1, -1):
        dia = hoy - timedelta(days=offset)
        es_finde = dia.weekday() >= 5  # 5=sábado, 6=domingo
        n_ventas_dia = random.randint(12, 15) if es_finde else random.randint(8, 11)
        for _ in range(n_ventas_dia):
            consecutivo += 1
            _generar_venta(
                db, dia, mesero, cajero, estado_entregado, mesas, productos, metodos, consecutivo
            )
            total_ventas += 1

    n_semanas = max(1, round(dias / 7))
    total_gastos = 0
    n_gastos = random.randint(2 * n_semanas, 4 * n_semanas)
    for _ in range(n_gastos):
        dia = hoy - timedelta(days=random.randint(0, dias - 1))
        cat = random.choice(categorias_gasto)
        concepto = random.choice(
            CONCEPTOS_GASTO.get(cat.nombre_categoria, ["Gasto general"])
        )
        monto = Decimal(random.randint(200, 3000))
        db.add(
            Gasto(
                id_usuario=cajero.id_usuario,
                id_categoria_gasto=cat.id_categoria_gasto,
                concepto=concepto,
                monto=monto,
                fecha_gasto=_fecha_en_dia(dia, 8, 20),
            )
        )
        total_gastos += 1

    total_compras = 0
    n_compras = random.randint(1 * n_semanas, 2 * n_semanas)
    for idx in range(n_compras):
        dia = hoy - timedelta(days=random.randint(0, dias - 1))
        proveedor = random.choice(proveedores)
        compra = Compra(
            id_proveedor=proveedor.id_proveedor,
            id_usuario=cajero.id_usuario,
            fecha_compra=_fecha_en_dia(dia, 8, 18),
            total=Decimal("0.00"),
            folio_factura=f"FAC-{idx + 1:04d}" if random.random() < 0.7 else None,
        )
        db.add(compra)
        db.flush()

        n_lineas = random.randint(1, min(3, len(insumos)))
        insumos_compra = random.sample(insumos, k=n_lineas)
        total_compra = Decimal("0.00")
        for insumo in insumos_compra:
            cantidad = Decimal(random.randint(5, 50))
            costo = insumo.costo_unitario
            db.add(
                DetalleCompra(
                    id_compra=compra.id_compra,
                    id_insumo=insumo.id_insumo,
                    cantidad=cantidad,
                    costo_unitario=costo,
                )
            )
            total_compra += cantidad * costo
        compra.total = total_compra
        total_compras += 1

    db.flush()
    return {
        "ventas": total_ventas,
        "gastos": total_gastos,
        "compras": total_compras,
        "omitido": False,
    }


def seed_demo(db, dias: int = DIAS_DEFAULT) -> dict:
    """Punto de entrada único: garantiza prerequisitos (`seed_base`), siembra
    insumos y genera transacciones de los últimos `dias` días, todo sobre la
    MISMA sesión `db` (no abre `SessionLocal`, no hace commit)."""
    seed_base(db)
    n_insumos = seed_insumos(db)
    resultado = seed_transacciones(db, dias=dias)
    resultado["insumos"] = n_insumos
    return resultado


def run(dias: int = DIAS_DEFAULT):
    db = SessionLocal()
    try:
        resultado = seed_demo(db, dias=dias)
        db.commit()
        if resultado["omitido"]:
            print(
                f"Datos demo ya presentes ({db.query(Venta).count()} ventas): omitido."
            )
        else:
            print(
                f"Seed demo: {resultado['ventas']} ventas, {resultado['gastos']} gastos, "
                f"{resultado['compras']} compras, {resultado['insumos']} insumos."
            )
    finally:
        db.close()


if __name__ == "__main__":
    run()
