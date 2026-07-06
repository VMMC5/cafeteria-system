from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class RecetaLineaCreate(BaseModel):
    id_insumo: int
    cantidad_requerida: Decimal = Field(gt=0)


class UnidadAbrev(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    abreviatura: str


class InsumoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_insumo: int
    nombre_insumo: str
    unidad: UnidadAbrev


class RecetaLineaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto_insumo: int
    id_insumo: int
    insumo: InsumoResumen
    cantidad_requerida: Decimal
