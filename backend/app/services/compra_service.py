from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Proveedor
from app.schemas.compra import ProveedorCreate

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
