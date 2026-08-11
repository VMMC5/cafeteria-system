from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Cancelacion,
    DetallePedido,
    EstadoPedido,
    Mesa,
    Pedido,
    Producto,
    Venta,
)
from app.schemas.pedido import PedidoCreate
from app.services import receta_service


def _estado_pendiente(db: Session) -> EstadoPedido:
    return db.execute(
        select(EstadoPedido).where(EstadoPedido.nombre_estado == "Pendiente")
    ).scalar_one()


def get_or_404(db: Session, id_pedido: int) -> Pedido:
    obj = db.get(Pedido, id_pedido)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return obj


# estado_origen -> (estado_destino permitido, {roles autorizados})
_FLUJO: dict[str, tuple[str, set[str]]] = {
    "Pendiente": ("En preparación", {"Cocinero", "Administrador"}),
    "En preparación": ("Listo", {"Cocinero", "Administrador"}),
    "Listo": ("Entregado", {"Mesero", "Administrador"}),
}

_CANCELABLE_ROLES = {"Mesero", "Administrador"}
_TERMINALES = {"Entregado", "Cancelado"}


def _estado_por_nombre(db: Session, nombre: str) -> EstadoPedido:
    return db.execute(
        select(EstadoPedido).where(EstadoPedido.nombre_estado == nombre)
    ).scalar_one()


def cambiar_estado(
    db: Session, id_pedido: int, id_estado_destino: int, usuario
) -> Pedido:
    pedido = get_or_404(db, id_pedido)
    destino = db.get(EstadoPedido, id_estado_destino)
    if destino is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Estado inválido")

    transicion = _FLUJO.get(pedido.estado.nombre_estado)
    if transicion is None or destino.nombre_estado != transicion[0]:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Transición de estado no permitida"
        )

    _, roles = transicion
    if usuario.rol.nombre_rol not in roles:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para esta transición"
        )

    pedido.id_estado = destino.id_estado
    db.commit()
    db.refresh(pedido)
    return pedido


def list_pedidos(
    db: Session,
    estados: list[int] | None = None,
    id_usuario: int | None = None,
) -> list[Pedido]:
    stmt = select(Pedido).order_by(Pedido.id_pedido.desc())
    if estados:
        stmt = stmt.where(Pedido.id_estado.in_(estados))
    if id_usuario is not None:
        stmt = stmt.where(Pedido.id_usuario == id_usuario)
    return list(db.execute(stmt).scalars())


def crear(db: Session, data: PedidoCreate, id_usuario: int) -> Pedido:
    mesa = db.get(Mesa, data.id_mesa)
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    # Una mesa Ocupada acepta rondas adicionales: cada pedido nuevo fluye
    # completo por cocina y caja; la mesa se libera al cerrar el último.
    if mesa.estado not in ("Disponible", "Ocupada"):
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

    requerido = receta_service.requerido_y_validar(db, lineas)

    pedido = Pedido(
        id_mesa=mesa.id_mesa,
        id_usuario=id_usuario,
        id_estado=_estado_pendiente(db).id_estado,
        observaciones=data.observaciones,
        detalle=lineas,
    )
    mesa.estado = "Ocupada"
    db.add(pedido)
    db.flush()
    receta_service.aplicar_descuento(db, pedido, requerido, id_usuario)
    db.commit()
    db.refresh(pedido)
    return pedido


def cancelar(db: Session, id_pedido: int, motivo: str, usuario) -> Pedido:
    pedido = get_or_404(db, id_pedido)
    if pedido.estado.nombre_estado in _TERMINALES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "El pedido no se puede cancelar en su estado actual",
        )
    if usuario.rol.nombre_rol not in _CANCELABLE_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para cancelar"
        )

    db.add(
        Cancelacion(
            id_pedido=pedido.id_pedido,
            id_usuario=usuario.id_usuario,
            motivo=motivo,
        )
    )
    pedido.id_estado = _estado_por_nombre(db, "Cancelado").id_estado
    pedido.mesa.estado = "Disponible"
    receta_service.reponer_pedido(db, pedido, usuario.id_usuario)
    db.commit()
    db.refresh(pedido)
    return pedido


def condiciones_pedido_activo(db: Session) -> tuple:
    """Condiciones que definen un pedido **activo**: ni cancelado ni cobrado.

    Única definición de la regla. La comparten `venta_service.listar_por_cobrar`
    y el guard de estado de mesas: si divergieran, la API podría liberar una mesa
    que en realidad sigue ocupada.
    """
    cancelado = db.execute(
        select(EstadoPedido.id_estado).where(
            EstadoPedido.nombre_estado == "Cancelado"
        )
    ).scalar_one()
    return (
        Pedido.id_estado != cancelado,
        Pedido.id_pedido.not_in(select(Venta.id_pedido)),
    )


def tiene_pedido_activo(db: Session, id_mesa: int) -> bool:
    """True si la mesa tiene al menos un pedido activo (ni cancelado ni cobrado)."""
    stmt = select(Pedido.id_pedido).where(
        Pedido.id_mesa == id_mesa, *condiciones_pedido_activo(db)
    )
    return db.execute(stmt).first() is not None
