from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.compra import CompraCreate, CompraOut
from app.services import compra_service

router = APIRouter(prefix="/compras", tags=["compras"])


@router.post("", response_model=CompraOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: CompraCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return compra_service.crear_compra(db, data, current)


@router.get("", response_model=list[CompraOut])
def listar(
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return compra_service.listar_compras(db, current)
