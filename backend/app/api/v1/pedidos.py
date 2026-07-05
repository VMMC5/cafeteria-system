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
