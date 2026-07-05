from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Categoria, Producto
from app.schemas.producto import ProductoCreate, ProductoUpdate


def _ensure_categoria(db: Session, id_categoria: int) -> None:
    if db.get(Categoria, id_categoria) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "La categoría no existe"
        )


def get_or_404(db: Session, id_producto: int) -> Producto:
    obj = db.get(Producto, id_producto)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return obj


def list_productos(
    db: Session, id_categoria: int | None = None, disponible: bool | None = None
) -> list[Producto]:
    stmt = select(Producto).order_by(Producto.id_producto)
    if id_categoria is not None:
        stmt = stmt.where(Producto.id_categoria == id_categoria)
    if disponible is not None:
        stmt = stmt.where(Producto.disponible == disponible)
    return list(db.execute(stmt).scalars())


def create(db: Session, data: ProductoCreate) -> Producto:
    _ensure_categoria(db, data.id_categoria)
    obj = Producto(
        id_categoria=data.id_categoria,
        nombre_producto=data.nombre_producto,
        descripcion=data.descripcion,
        precio_venta=data.precio_venta,
        disponible=data.disponible,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, id_producto: int, data: ProductoUpdate) -> Producto:
    obj = get_or_404(db, id_producto)
    if data.id_categoria is not None:
        _ensure_categoria(db, data.id_categoria)
    for campo in (
        "id_categoria",
        "nombre_producto",
        "descripcion",
        "precio_venta",
        "disponible",
    ):
        valor = getattr(data, campo)
        if valor is not None:
            setattr(obj, campo, valor)
    db.commit()
    db.refresh(obj)
    return obj


def soft_delete(db: Session, id_producto: int) -> Producto:
    obj = get_or_404(db, id_producto)
    obj.disponible = False
    db.commit()
    db.refresh(obj)
    return obj
