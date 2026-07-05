from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Insumo, MovimientoInventario, UnidadMedida
from app.schemas.insumo import InsumoCreate, InsumoUpdate, MovimientoCreate

_ROLES_INV = {"Cocinero", "Administrador"}
_TIPOS = {"Entrada", "Salida"}
_MOTIVOS_MANUAL = {"Ajuste", "Merma"}


def _check_rol(usuario) -> None:
    if usuario.rol.nombre_rol not in _ROLES_INV:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para inventario"
        )


def listar_unidades(db: Session) -> list[UnidadMedida]:
    return list(
        db.execute(
            select(UnidadMedida).order_by(UnidadMedida.id_unidad)
        ).scalars()
    )


def get_or_404(db: Session, id_insumo: int) -> Insumo:
    obj = db.get(Insumo, id_insumo)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Insumo no encontrado")
    return obj


def listar(db: Session, usuario) -> list[Insumo]:
    _check_rol(usuario)
    return list(db.execute(select(Insumo).order_by(Insumo.nombre_insumo)).scalars())


def obtener(db: Session, id_insumo: int, usuario) -> Insumo:
    _check_rol(usuario)
    return get_or_404(db, id_insumo)


def crear(db: Session, data: InsumoCreate, usuario) -> Insumo:
    _check_rol(usuario)
    if db.get(UnidadMedida, data.id_unidad) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Unidad de medida inexistente"
        )
    insumo = Insumo(
        nombre_insumo=data.nombre_insumo,
        id_unidad=data.id_unidad,
        descripcion=data.descripcion,
        stock_actual=data.stock_actual,
        stock_minimo=data.stock_minimo,
        costo_unitario=data.costo_unitario,
    )
    db.add(insumo)
    db.commit()
    db.refresh(insumo)
    return insumo


def actualizar(db: Session, id_insumo: int, data: InsumoUpdate, usuario) -> Insumo:
    _check_rol(usuario)
    insumo = get_or_404(db, id_insumo)
    if data.nombre_insumo is not None:
        insumo.nombre_insumo = data.nombre_insumo
    if data.descripcion is not None:
        insumo.descripcion = data.descripcion
    if data.stock_minimo is not None:
        insumo.stock_minimo = data.stock_minimo
    if data.costo_unitario is not None:
        insumo.costo_unitario = data.costo_unitario
    db.commit()
    db.refresh(insumo)
    return insumo


def registrar_movimiento(
    db: Session, id_insumo: int, data: MovimientoCreate, usuario
) -> Insumo:
    _check_rol(usuario)
    insumo = get_or_404(db, id_insumo)
    if data.tipo not in _TIPOS or data.motivo not in _MOTIVOS_MANUAL:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Tipo o motivo inválido"
        )
    if data.tipo == "Salida" and data.cantidad > insumo.stock_actual:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Stock insuficiente"
        )
    delta = data.cantidad if data.tipo == "Entrada" else -data.cantidad
    insumo.stock_actual = insumo.stock_actual + delta
    db.add(
        MovimientoInventario(
            id_insumo=insumo.id_insumo,
            id_usuario=usuario.id_usuario,
            tipo_movimiento=data.tipo,
            motivo=data.motivo,
            cantidad=data.cantidad,
        )
    )
    db.commit()
    db.refresh(insumo)
    return insumo
