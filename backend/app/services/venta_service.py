from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Configuracion,
    MetodoPago,
    Pago,
    Pedido,
    Ticket,
    Venta,
)
from app.schemas.venta import PagoOut, VentaCreate, VentaOut
from app.services import pedido_service

_IVA_DEFAULT = Decimal("0.16")
_ROLES_COBRO = {"Cajero", "Administrador"}


def _iva_tasa(db: Session) -> Decimal:
    row = db.execute(
        select(Configuracion).where(Configuracion.clave == "iva_tasa")
    ).scalar_one_or_none()
    return Decimal(row.valor) if row else _IVA_DEFAULT


def desglose(total: Decimal, tasa: Decimal) -> tuple[Decimal, Decimal]:
    base = (total / (Decimal("1") + tasa)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    iva = total - base
    return base, iva


def get_or_404(db: Session, id_venta: int) -> Venta:
    obj = db.get(Venta, id_venta)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    return obj


def cobrar(db: Session, data: VentaCreate, usuario) -> Venta:
    if usuario.rol.nombre_rol not in _ROLES_COBRO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol no autorizado para cobrar")

    ids = data.ids_pedidos
    if len(set(ids)) != len(ids):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Pedidos repetidos en el cobro"
        )

    pedidos: list[Pedido] = []
    for id_pedido in ids:
        pedido = db.get(Pedido, id_pedido)
        if pedido is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
        pedidos.append(pedido)

    for pedido in pedidos:
        if pedido.estado.nombre_estado == "Cancelado":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "No se puede cobrar un pedido cancelado"
            )
        if pedido.id_venta is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya fue cobrado")

    if len({p.id_mesa for p in pedidos}) > 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Los pedidos del cobro deben ser de la misma mesa"
        )
    # La cuenta completa (más de una ronda) exige todo Entregado; la ronda
    # suelta conserva la regla histórica (cobrable en cualquier estado no
    # cancelado) para no romper el flujo existente.
    if len(pedidos) > 1 and any(
        p.estado.nombre_estado != "Entregado" for p in pedidos
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La mesa tiene una ronda sin entregar"
        )

    for p in data.pagos:
        if db.get(MetodoPago, p.id_metodo_pago) is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Método de pago {p.id_metodo_pago} inexistente",
            )

    total = sum((p.total for p in pedidos), Decimal("0"))
    suma = sum((p.monto for p in data.pagos), Decimal("0"))
    if suma < total:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pago insuficiente")

    venta = Venta(id_usuario=usuario.id_usuario, total=total)
    db.add(venta)
    db.flush()
    for pedido in pedidos:
        pedido.id_venta = venta.id_venta
    for p in data.pagos:
        db.add(
            Pago(
                id_venta=venta.id_venta,
                id_metodo_pago=p.id_metodo_pago,
                monto=p.monto,
                referencia=p.referencia,
            )
        )
    db.add(Ticket(id_venta=venta.id_venta, folio=f"V-{venta.id_venta:06d}"))
    # La mesa se libera solo si fuera de esta cuenta no queda ronda activa
    # (el id_venta recién asignado puede no estar flusheado: exclusión explícita).
    if not pedido_service.tiene_pedido_activo(
        db, pedidos[0].id_mesa, excepto_ids=[p.id_pedido for p in pedidos]
    ):
        pedidos[0].mesa.estado = "Disponible"
    db.commit()
    db.refresh(venta)
    return venta


def to_out(db: Session, venta: Venta) -> VentaOut:
    base, iva = desglose(venta.total, _iva_tasa(db))
    suma = sum((p.monto for p in venta.pagos), Decimal("0"))
    return VentaOut(
        id_venta=venta.id_venta,
        ids_pedidos=[p.id_pedido for p in venta.pedidos],
        fecha_venta=venta.fecha_venta,
        estado_venta=venta.estado_venta,
        folio=venta.ticket.folio,
        total=venta.total,
        subtotal=base,
        iva=iva,
        cambio=suma - venta.total,
        pagos=[PagoOut.model_validate(p) for p in venta.pagos],
    )


def listar_por_cobrar(db: Session) -> list[Pedido]:
    stmt = (
        select(Pedido)
        .where(*pedido_service.condiciones_pedido_activo(db))
        .order_by(Pedido.id_pedido.desc())
    )
    return list(db.execute(stmt).scalars())
