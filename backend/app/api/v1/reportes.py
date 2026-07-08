from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.reporte import (
    ComparativoOut,
    EstadoResultadoOut,
    GastoDetalleOut,
    GastoPorDiaOut,
    InventarioNivelOut,
    ResumenOut,
    TopProductoOut,
    VentaDetalleOut,
    VentaPorDiaOut,
)
from app.services import reporte_service

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/resumen", response_model=ResumenOut)
def resumen(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.resumen(db, d, h)


@router.get("/ventas-por-dia", response_model=list[VentaPorDiaOut])
def ventas_por_dia(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.ventas_por_dia(db, d, h)


@router.get("/gastos-por-dia", response_model=list[GastoPorDiaOut])
def gastos_por_dia(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.gastos_por_dia(db, d, h)


@router.get("/top-productos", response_model=list[TopProductoOut])
def top_productos(
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.top_productos(db, d, h, limite)


@router.get("/ventas", response_model=list[VentaDetalleOut])
def detalle_ventas(
    desde: date | None = None,
    hasta: date | None = None,
    id_usuario: int | None = None,
    id_metodo: int | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.detalle_ventas(db, d, h, id_usuario, id_metodo)


@router.get("/gastos", response_model=list[GastoDetalleOut])
def detalle_gastos(
    desde: date | None = None,
    hasta: date | None = None,
    id_usuario: int | None = None,
    id_categoria: int | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.detalle_gastos(db, d, h, id_usuario, id_categoria)


@router.get("/comparativo", response_model=ComparativoOut)
def comparativo(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.comparativo(db, d, h)


@router.get("/inventario-niveles", response_model=list[InventarioNivelOut])
def inventario_niveles(
    solo_bajo_minimo: bool = False,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return reporte_service.inventario_niveles(db, solo_bajo_minimo)


@router.get("/estado-resultados", response_model=list[EstadoResultadoOut])
def estado_resultados(
    desde: date | None = None,
    hasta: date | None = None,
    agrupar: Literal["dia", "semana", "mes"] = "dia",
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.estado_resultados(db, d, h, agrupar)
