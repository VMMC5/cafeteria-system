from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Mesa, Pedido
from app.schemas.mesa import MesaCreate, MesaUpdate
from app.services import pedido_service


def list_mesas(db: Session, estado: str | None = None) -> list[Mesa]:
    stmt = select(Mesa).order_by(Mesa.numero_mesa)
    if estado:
        stmt = stmt.where(Mesa.estado == estado)
    return list(db.execute(stmt).scalars())


def get_or_404(db: Session, id_mesa: int) -> Mesa:
    obj = db.get(Mesa, id_mesa)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    return obj


def _ensure_unico(db: Session, numero: int, exclude_id: int | None = None) -> None:
    existing = db.execute(
        select(Mesa).where(Mesa.numero_mesa == numero)
    ).scalar_one_or_none()
    if existing is not None and existing.id_mesa != exclude_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "El número de mesa ya existe")


def create(db: Session, data: MesaCreate) -> Mesa:
    _ensure_unico(db, data.numero_mesa)
    obj = Mesa(
        numero_mesa=data.numero_mesa,
        capacidad=data.capacidad,
        ubicacion=data.ubicacion,
        estado=data.estado,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, id_mesa: int, data: MesaUpdate) -> Mesa:
    obj = get_or_404(db, id_mesa)
    if data.numero_mesa is not None:
        _ensure_unico(db, data.numero_mesa, exclude_id=id_mesa)
    if data.estado is not None and data.estado != obj.estado:
        # "Ocupada" no se asigna a mano: lo pone el sistema al crear un pedido y
        # lo quita el cobro o la cancelación.
        if data.estado == "Ocupada":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "El estado Ocupada lo asigna el sistema al crear un pedido",
            )
        # Se consulta el pedido real, no la bandera de la mesa: así una mesa que
        # quedó marcada Ocupada sin pedido activo se puede corregir.
        if pedido_service.tiene_pedido_activo(db, id_mesa):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La mesa tiene un pedido activo; su estado lo gestiona el sistema",
            )
    for campo in ("numero_mesa", "capacidad", "ubicacion", "estado"):
        valor = getattr(data, campo)
        if valor is not None:
            setattr(obj, campo, valor)
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, id_mesa: int) -> None:
    obj = get_or_404(db, id_mesa)
    tiene_pedidos = db.execute(
        select(Pedido).where(Pedido.id_mesa == id_mesa)
    ).first()
    if tiene_pedidos:
        raise HTTPException(status.HTTP_409_CONFLICT, "La mesa tiene pedidos asociados")
    db.delete(obj)
    db.commit()
