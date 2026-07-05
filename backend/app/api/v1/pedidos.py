from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.pedido import PedidoCreate, PedidoOut
from app.services import pedido_service

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.crear(db, data, current.id_usuario)


@router.get("", response_model=list[PedidoOut])
def listar(
    id_estado: int | None = None,
    mias: bool = False,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    id_usuario = current.id_usuario if mias else None
    return pedido_service.list_pedidos(db, id_estado, id_usuario)


@router.get("/{id_pedido}", response_model=PedidoOut)
def detalle(
    id_pedido: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.get_or_404(db, id_pedido)
