from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ResumenOut(BaseModel):
    total_vendido: Decimal
    num_ventas: int
    ticket_promedio: Decimal
    total_gastos: Decimal
    total_compras: Decimal
    utilidad_estimada: Decimal


class VentaPorDiaOut(BaseModel):
    fecha: date
    total: Decimal
    num_ventas: int


class GastoPorDiaOut(BaseModel):
    fecha: date
    total: Decimal
    num_gastos: int


class TopProductoOut(BaseModel):
    id_producto: int
    nombre: str
    cantidad: int
    importe: Decimal


class VentaDetalleOut(BaseModel):
    folio: str
    fecha: datetime
    mesa: int | None
    total: Decimal
    metodos: str


class GastoDetalleOut(BaseModel):
    fecha: datetime
    categoria: str
    concepto: str
    monto: Decimal


class DeltasOut(BaseModel):
    total_vendido: float | None
    total_gastos: float | None
    utilidad_estimada: float | None
    num_ventas: float | None


class ComparativoOut(BaseModel):
    actual: ResumenOut
    anterior: ResumenOut
    deltas: DeltasOut


class InventarioNivelOut(BaseModel):
    nombre: str
    unidad: str
    stock_actual: Decimal
    stock_minimo: Decimal
    nivel_pct: int
    bajo_minimo: bool
