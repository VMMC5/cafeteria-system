from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.mesa import MesaCreate, MesaOut, MesaUpdate
from app.services import mesa_service

router = APIRouter(prefix="/mesas", tags=["mesas"])


@router.get("", response_model=list[MesaOut])
def listar(
    estado: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return mesa_service.list_mesas(db, estado)


@router.get("/{id_mesa}", response_model=MesaOut)
def detalle(
    id_mesa: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return mesa_service.get_or_404(db, id_mesa)


@router.post("", response_model=MesaOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: MesaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return mesa_service.create(db, data)


@router.patch("/{id_mesa}", response_model=MesaOut)
def editar(
    id_mesa: int,
    data: MesaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return mesa_service.update(db, id_mesa, data)


@router.delete("/{id_mesa}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(
    id_mesa: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    mesa_service.delete(db, id_mesa)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
