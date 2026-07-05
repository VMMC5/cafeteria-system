from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Categoria, Producto
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate


def list_categorias(db: Session) -> list[Categoria]:
    return list(db.execute(select(Categoria).order_by(Categoria.id_categoria)).scalars())


def get_or_404(db: Session, id_categoria: int) -> Categoria:
    obj = db.get(Categoria, id_categoria)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    return obj


def _ensure_unico(db: Session, nombre: str, exclude_id: int | None = None) -> None:
    existing = db.execute(
        select(Categoria).where(Categoria.nombre_categoria == nombre)
    ).scalar_one_or_none()
    if existing is not None and existing.id_categoria != exclude_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "La categoría ya existe")


def create(db: Session, data: CategoriaCreate) -> Categoria:
    _ensure_unico(db, data.nombre_categoria)
    obj = Categoria(nombre_categoria=data.nombre_categoria, descripcion=data.descripcion)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, id_categoria: int, data: CategoriaUpdate) -> Categoria:
    obj = get_or_404(db, id_categoria)
    if data.nombre_categoria is not None:
        _ensure_unico(db, data.nombre_categoria, exclude_id=id_categoria)
        obj.nombre_categoria = data.nombre_categoria
    if data.descripcion is not None:
        obj.descripcion = data.descripcion
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, id_categoria: int) -> None:
    obj = get_or_404(db, id_categoria)
    tiene_productos = db.execute(
        select(Producto).where(Producto.id_categoria == id_categoria)
    ).first()
    if tiene_productos:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La categoría tiene productos asociados"
        )
    db.delete(obj)
    db.commit()
