from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Compra,
    DetalleCompra,
    Insumo,
    MovimientoInventario,
    Proveedor,
)
from app.schemas.compra import CompraCreate, ProveedorCreate

_ROLES_INV = {"Cocinero", "Administrador"}


def _check_rol(usuario) -> None:
    if usuario.rol.nombre_rol not in _ROLES_INV:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para compras"
        )


def listar_proveedores(db: Session, usuario) -> list[Proveedor]:
    _check_rol(usuario)
    return list(
        db.execute(select(Proveedor).order_by(Proveedor.nombre_proveedor)).scalars()
    )


def crear_proveedor(db: Session, data: ProveedorCreate, usuario) -> Proveedor:
    _check_rol(usuario)
    prov = Proveedor(
        nombre_proveedor=data.nombre_proveedor,
        telefono=data.telefono,
        correo=data.correo,
        direccion=data.direccion,
    )
    db.add(prov)
    db.commit()
    db.refresh(prov)
    return prov


def crear_compra(db: Session, data: CompraCreate, usuario) -> Compra:
    _check_rol(usuario)
    if db.get(Proveedor, data.id_proveedor) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Proveedor inexistente"
        )
    insumos = {}
    for item in data.items:
        insumo = db.get(Insumo, item.id_insumo)
        if insumo is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Insumo {item.id_insumo} inexistente",
            )
        insumos[item.id_insumo] = insumo

    total = sum(
        (it.cantidad * it.costo_unitario for it in data.items), Decimal("0")
    )
    compra = Compra(
        id_proveedor=data.id_proveedor,
        id_usuario=usuario.id_usuario,
        total=total,
        folio_factura=data.folio_factura,
    )
    db.add(compra)
    db.flush()
    for item in data.items:
        db.add(
            DetalleCompra(
                id_compra=compra.id_compra,
                id_insumo=item.id_insumo,
                cantidad=item.cantidad,
                costo_unitario=item.costo_unitario,
            )
        )
        insumo = insumos[item.id_insumo]
        insumo.stock_actual = insumo.stock_actual + item.cantidad
        insumo.costo_unitario = item.costo_unitario
        db.add(
            MovimientoInventario(
                id_insumo=item.id_insumo,
                id_usuario=usuario.id_usuario,
                id_compra=compra.id_compra,
                tipo_movimiento="Entrada",
                motivo="Compra",
                cantidad=item.cantidad,
            )
        )
    db.commit()
    db.refresh(compra)
    return compra


def listar_compras(db: Session, usuario) -> list[Compra]:
    _check_rol(usuario)
    return list(db.execute(select(Compra).order_by(Compra.id_compra.desc())).scalars())
