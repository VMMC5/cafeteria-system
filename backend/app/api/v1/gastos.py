from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.gasto import CategoriaGastoOut, GastoCreate, GastoOut
from app.services import gasto_service

router = APIRouter(prefix="/gastos", tags=["gastos"])


@router.get("/categorias", response_model=list[CategoriaGastoOut])
def listar_categorias(
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return gasto_service.listar_categorias(db)


@router.post("", response_model=GastoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: GastoCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return gasto_service.crear(db, data, current)


@router.get("", response_model=list[GastoOut])
def listar(
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return gasto_service.listar(db, current)
