from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.insumo import (
    InsumoCreate,
    InsumoOut,
    InsumoUpdate,
    MovimientoCreate,
)
from app.services import insumo_service

router = APIRouter(prefix="/insumos", tags=["insumos"])


@router.get("", response_model=list[InsumoOut])
def listar(
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return insumo_service.listar(db, current)


@router.get("/{id_insumo}", response_model=InsumoOut)
def detalle(
    id_insumo: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return insumo_service.obtener(db, id_insumo, current)


@router.post("", response_model=InsumoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: InsumoCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return insumo_service.crear(db, data, current)


@router.patch("/{id_insumo}", response_model=InsumoOut)
def editar(
    id_insumo: int,
    data: InsumoUpdate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return insumo_service.actualizar(db, id_insumo, data, current)


@router.post("/{id_insumo}/movimientos", response_model=InsumoOut)
def registrar_movimiento(
    id_insumo: int,
    data: MovimientoCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return insumo_service.registrar_movimiento(db, id_insumo, data, current)
