from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.producto import ProductoCreate, ProductoOut, ProductoUpdate
from app.services import producto_service

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=list[ProductoOut])
def listar(
    id_categoria: int | None = None,
    disponible: bool | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return producto_service.list_productos(db, id_categoria, disponible)


@router.get("/{id_producto}", response_model=ProductoOut)
def detalle(
    id_producto: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return producto_service.get_or_404(db, id_producto)


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return producto_service.create(db, data)


@router.patch("/{id_producto}", response_model=ProductoOut)
def editar(
    id_producto: int,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return producto_service.update(db, id_producto, data)


@router.delete("/{id_producto}", response_model=ProductoOut)
def desactivar(
    id_producto: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return producto_service.soft_delete(db, id_producto)
