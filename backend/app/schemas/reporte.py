from datetime import date
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


class TopProductoOut(BaseModel):
    id_producto: int
    nombre: str
    cantidad: int
    importe: Decimal
