from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.pedido import (
    CancelacionCreate,
    EstadoUpdate,
    PedidoCreate,
    PedidoOut,
)
from app.services import pedido_service

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.crear(db, data, current.id_usuario)


@router.patch("/{id_pedido}/estado", response_model=PedidoOut)
def cambiar_estado(
    id_pedido: int,
    data: EstadoUpdate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.cambiar_estado(db, id_pedido, data.id_estado, current)


@router.post("/{id_pedido}/cancelar", response_model=PedidoOut)
def cancelar(
    id_pedido: int,
    data: CancelacionCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.cancelar(db, id_pedido, data.motivo, current)


@router.get("", response_model=list[PedidoOut])
def listar(
    id_estado: int | None = None,
    estados: str | None = None,
    mias: bool = False,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    id_usuario = current.id_usuario if mias else None
    if estados:
        ids = [int(x) for x in estados.split(",") if x.strip()]
    elif id_estado is not None:
        ids = [id_estado]
    else:
        ids = None
    return pedido_service.list_pedidos(db, ids, id_usuario)


@router.get("/{id_pedido}", response_model=PedidoOut)
def detalle(
    id_pedido: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.get_or_404(db, id_pedido)
