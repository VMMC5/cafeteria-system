from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PagoIn(BaseModel):
    id_metodo_pago: int
    monto: Decimal = Field(gt=0)
    referencia: str | None = None


class VentaCreate(BaseModel):
    ids_pedidos: list[int] = Field(min_length=1)
    pagos: list[PagoIn] = Field(min_length=1)


class MetodoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_metodo_pago: int
    nombre_metodo: str


class PagoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_pago: int
    id_metodo_pago: int
    metodo: MetodoResumen
    monto: Decimal
    referencia: str | None


class VentaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_venta: int
    ids_pedidos: list[int]
    fecha_venta: datetime
    estado_venta: str
    folio: str
    total: Decimal
    subtotal: Decimal
    iva: Decimal
    cambio: Decimal
    pagos: list[PagoOut]
