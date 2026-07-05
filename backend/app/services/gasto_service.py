from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CategoriaGasto, Gasto
from app.schemas.gasto import GastoCreate

_ROLES_GASTO = {"Cajero", "Administrador"}


def _check_rol(usuario) -> None:
    if usuario.rol.nombre_rol not in _ROLES_GASTO:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para gastos"
        )


def listar_categorias(db: Session) -> list[CategoriaGasto]:
    return list(
        db.execute(
            select(CategoriaGasto).order_by(CategoriaGasto.id_categoria_gasto)
        ).scalars()
    )


def crear(db: Session, data: GastoCreate, usuario) -> Gasto:
    _check_rol(usuario)
    if db.get(CategoriaGasto, data.id_categoria_gasto) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Categoría de gasto inexistente"
        )
    gasto = Gasto(
        id_usuario=usuario.id_usuario,
        id_categoria_gasto=data.id_categoria_gasto,
        concepto=data.concepto,
        monto=data.monto,
    )
    db.add(gasto)
    db.commit()
    db.refresh(gasto)
    return gasto


def listar(db: Session, usuario) -> list[Gasto]:
    _check_rol(usuario)
    return list(db.execute(select(Gasto).order_by(Gasto.id_gasto.desc())).scalars())
