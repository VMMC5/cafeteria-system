from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import EstadoPedido, Usuario
from app.schemas.estado import EstadoOut

router = APIRouter(prefix="/estados", tags=["estados"])


@router.get("", response_model=list[EstadoOut])
def listar(
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return list(
        db.execute(select(EstadoPedido).order_by(EstadoPedido.id_estado)).scalars()
    )
