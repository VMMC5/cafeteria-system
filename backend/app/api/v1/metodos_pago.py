from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import MetodoPago, Usuario
from app.schemas.venta import MetodoResumen

router = APIRouter(prefix="/metodos_pago", tags=["metodos_pago"])


@router.get("", response_model=list[MetodoResumen])
def listar(
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return list(
        db.execute(
            select(MetodoPago).order_by(MetodoPago.id_metodo_pago)
        ).scalars()
    )
