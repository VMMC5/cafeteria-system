from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.categoria import CategoriaCreate, CategoriaOut, CategoriaUpdate
from app.services import categoria_service

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("", response_model=list[CategoriaOut])
def listar(db: Session = Depends(get_db), _: Usuario = Depends(deps.get_current_user)):
    return categoria_service.list_categorias(db)


@router.get("/{id_categoria}", response_model=CategoriaOut)
def detalle(
    id_categoria: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return categoria_service.get_or_404(db, id_categoria)


@router.post("", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return categoria_service.create(db, data)


@router.patch("/{id_categoria}", response_model=CategoriaOut)
def editar(
    id_categoria: int,
    data: CategoriaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return categoria_service.update(db, id_categoria, data)


@router.delete("/{id_categoria}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(
    id_categoria: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    categoria_service.delete(db, id_categoria)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
