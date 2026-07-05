from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PedidoItemCreate(BaseModel):
    id_producto: int
    cantidad: int = Field(ge=1)
    observaciones: str | None = None


class PedidoCreate(BaseModel):
    id_mesa: int
    observaciones: str | None = None
    items: list[PedidoItemCreate] = Field(min_length=1)


class ProductoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    nombre_producto: str


class DetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_detalle: int
    id_producto: int
    producto: ProductoResumen
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    observaciones: str | None


class MesaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_mesa: int
    numero_mesa: int


class EstadoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_estado: int
    nombre_estado: str


class PedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_pedido: int
    id_mesa: int
    mesa: MesaResumen
    id_estado: int
    estado: EstadoResumen
    id_usuario: int
    fecha_pedido: datetime
    observaciones: str | None
    detalle: list[DetalleOut]
    total: Decimal
