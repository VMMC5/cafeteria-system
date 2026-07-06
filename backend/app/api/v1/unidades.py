from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.insumo import UnidadOut
from app.services import insumo_service

router = APIRouter(prefix="/unidades", tags=["unidades"])


@router.get("", response_model=list[UnidadOut])
def listar(
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return insumo_service.listar_unidades(db)
