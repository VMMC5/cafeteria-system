from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProveedorCreate(BaseModel):
    nombre_proveedor: str = Field(min_length=1)
    telefono: str | None = None
    correo: str | None = None
    direccion: str | None = None


class ProveedorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_proveedor: int
    nombre_proveedor: str
    telefono: str | None
    correo: str | None
    direccion: str | None


class CompraItemIn(BaseModel):
    id_insumo: int
    cantidad: Decimal = Field(gt=0)
    costo_unitario: Decimal = Field(ge=0)


class CompraCreate(BaseModel):
    id_proveedor: int
    folio_factura: str | None = None
    items: list[CompraItemIn] = Field(min_length=1)


class InsumoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_insumo: int
    nombre_insumo: str


class ProveedorResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_proveedor: int
    nombre_proveedor: str


class DetalleCompraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_detalle_compra: int
    id_insumo: int
    insumo: InsumoResumen
    cantidad: Decimal
    costo_unitario: Decimal
    subtotal: Decimal


class CompraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_compra: int
    id_proveedor: int
    proveedor: ProveedorResumen
    fecha_compra: datetime
    total: Decimal
    folio_factura: str | None
    detalle: list[DetalleCompraOut]
