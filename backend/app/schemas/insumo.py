from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class UnidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_unidad: int
    nombre_unidad: str
    abreviatura: str


class InsumoCreate(BaseModel):
    nombre_insumo: str = Field(min_length=1)
    id_unidad: int
    descripcion: str | None = None
    stock_actual: Decimal = Field(default=Decimal("0"), ge=0)
    stock_minimo: Decimal = Field(default=Decimal("0"), ge=0)
    costo_unitario: Decimal = Field(default=Decimal("0"), ge=0)


class InsumoUpdate(BaseModel):
    nombre_insumo: str | None = None
    descripcion: str | None = None
    stock_minimo: Decimal | None = Field(default=None, ge=0)
    costo_unitario: Decimal | None = Field(default=None, ge=0)


class InsumoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_insumo: int
    nombre_insumo: str
    id_unidad: int
    unidad: UnidadOut
    descripcion: str | None
    stock_actual: Decimal
    stock_minimo: Decimal
    costo_unitario: Decimal
