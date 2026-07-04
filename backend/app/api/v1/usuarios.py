from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.usuario import UsuarioCreate, UsuarioOut, UsuarioUpdate
from app.services import usuario_service

router = APIRouter(prefix="/usuarios", tags=["usuarios"])


@router.get("", response_model=list[UsuarioOut])
def listar(
    q: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return usuario_service.list_usuarios(db, q)


@router.post("", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return usuario_service.create_usuario(db, data)


@router.get("/{id_usuario}", response_model=UsuarioOut)
def detalle(
    id_usuario: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return usuario_service.get_or_404(db, id_usuario)


@router.patch("/{id_usuario}", response_model=UsuarioOut)
def editar(
    id_usuario: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(deps.require_admin),
):
    return usuario_service.update_usuario(db, id_usuario, data, actor.id_usuario)


@router.delete("/{id_usuario}", response_model=UsuarioOut)
def desactivar(
    id_usuario: int,
    db: Session = Depends(get_db),
    actor: Usuario = Depends(deps.require_admin),
):
    return usuario_service.soft_delete(db, id_usuario, actor.id_usuario)
