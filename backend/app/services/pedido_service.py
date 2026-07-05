from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DetallePedido, EstadoPedido, Mesa, Pedido, Producto
from app.schemas.pedido import PedidoCreate


def _estado_pendiente(db: Session) -> EstadoPedido:
    return db.execute(
        select(EstadoPedido).where(EstadoPedido.nombre_estado == "Pendiente")
    ).scalar_one()


def get_or_404(db: Session, id_pedido: int) -> Pedido:
    obj = db.get(Pedido, id_pedido)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return obj


def list_pedidos(
    db: Session, id_estado: int | None = None, id_usuario: int | None = None
) -> list[Pedido]:
    stmt = select(Pedido).order_by(Pedido.id_pedido.desc())
    if id_estado is not None:
        stmt = stmt.where(Pedido.id_estado == id_estado)
    if id_usuario is not None:
        stmt = stmt.where(Pedido.id_usuario == id_usuario)
    return list(db.execute(stmt).scalars())


def crear(db: Session, data: PedidoCreate, id_usuario: int) -> Pedido:
    mesa = db.get(Mesa, data.id_mesa)
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    if mesa.estado != "Disponible":
        raise HTTPException(status.HTTP_409_CONFLICT, "La mesa no está disponible")

    lineas = []
    for item in data.items:
        prod = db.get(Producto, item.id_producto)
        if prod is None or not prod.disponible:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"El producto {item.id_producto} no está disponible",
            )
        lineas.append(
            DetallePedido(
                id_producto=prod.id_producto,
                cantidad=item.cantidad,
                precio_unitario=prod.precio_venta,
                observaciones=item.observaciones,
            )
        )

    pedido = Pedido(
        id_mesa=mesa.id_mesa,
        id_usuario=id_usuario,
        id_estado=_estado_pendiente(db).id_estado,
        observaciones=data.observaciones,
        detalle=lineas,
    )
    mesa.estado = "Ocupada"
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido
