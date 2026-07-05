from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Configuracion,
    EstadoPedido,
    MetodoPago,
    Pago,
    Pedido,
    Ticket,
    Venta,
)
from app.schemas.venta import PagoOut, VentaCreate, VentaOut

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

    pedido = db.get(Pedido, data.id_pedido)
    if pedido is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    if pedido.estado.nombre_estado == "Cancelado":
        raise HTTPException(
            status.HTTP_409_CONFLICT, "No se puede cobrar un pedido cancelado"
        )
    ya = db.execute(
        select(Venta).where(Venta.id_pedido == pedido.id_pedido)
    ).scalar_one_or_none()
    if ya is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya fue cobrado")

    for p in data.pagos:
        if db.get(MetodoPago, p.id_metodo_pago) is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Método de pago {p.id_metodo_pago} inexistente",
            )

    total = pedido.total
    suma = sum((p.monto for p in data.pagos), Decimal("0"))
    if suma < total:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pago insuficiente")

    venta = Venta(
        id_pedido=pedido.id_pedido, id_usuario=usuario.id_usuario, total=total
    )
    db.add(venta)
    db.flush()
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
    pedido.mesa.estado = "Disponible"
    db.commit()
    db.refresh(venta)
    return venta


def to_out(db: Session, venta: Venta) -> VentaOut:
    base, iva = desglose(venta.total, _iva_tasa(db))
    suma = sum((p.monto for p in venta.pagos), Decimal("0"))
    return VentaOut(
        id_venta=venta.id_venta,
        id_pedido=venta.id_pedido,
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
    cancelado = db.execute(
        select(EstadoPedido.id_estado).where(
            EstadoPedido.nombre_estado == "Cancelado"
        )
    ).scalar_one()
    con_venta = select(Venta.id_pedido)
    stmt = (
        select(Pedido)
        .where(Pedido.id_estado != cancelado, Pedido.id_pedido.not_in(con_venta))
        .order_by(Pedido.id_pedido.desc())
    )
    return list(db.execute(stmt).scalars())
