from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Insumo, Producto, ProductoInsumo
from app.schemas.receta import RecetaLineaCreate

_ROLES_INV = {"Cocinero", "Administrador"}


def _check_rol(usuario) -> None:
    if usuario.rol.nombre_rol not in _ROLES_INV:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para recetas"
        )


def _producto_or_404(db: Session, id_producto: int) -> Producto:
    obj = db.get(Producto, id_producto)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return obj


def listar_receta(db: Session, id_producto: int, usuario) -> list[ProductoInsumo]:
    _check_rol(usuario)
    _producto_or_404(db, id_producto)
    return list(
        db.execute(
            select(ProductoInsumo)
            .where(ProductoInsumo.id_producto == id_producto)
            .order_by(ProductoInsumo.id_producto_insumo)
        ).scalars()
    )


def agregar_linea(
    db: Session, id_producto: int, data: RecetaLineaCreate, usuario
) -> ProductoInsumo:
    _check_rol(usuario)
    _producto_or_404(db, id_producto)
    if db.get(Insumo, data.id_insumo) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Insumo inexistente"
        )
    existe = db.execute(
        select(ProductoInsumo).where(
            ProductoInsumo.id_producto == id_producto,
            ProductoInsumo.id_insumo == data.id_insumo,
        )
    ).scalar_one_or_none()
    if existe is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El insumo ya está en la receta"
        )
    linea = ProductoInsumo(
        id_producto=id_producto,
        id_insumo=data.id_insumo,
        cantidad_requerida=data.cantidad_requerida,
    )
    db.add(linea)
    db.commit()
    db.refresh(linea)
    return linea


def eliminar_linea(
    db: Session, id_producto: int, id_producto_insumo: int, usuario
) -> None:
    _check_rol(usuario)
    linea = db.get(ProductoInsumo, id_producto_insumo)
    if linea is None or linea.id_producto != id_producto:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Línea de receta no encontrada"
        )
    db.delete(linea)
    db.commit()
