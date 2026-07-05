from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoriaGastoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria_gasto: int
    nombre_categoria: str


class GastoCreate(BaseModel):
    id_categoria_gasto: int
    concepto: str = Field(min_length=1)
    monto: Decimal = Field(gt=0)


class GastoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_gasto: int
    id_categoria_gasto: int
    categoria: CategoriaGastoOut
    concepto: str
    monto: Decimal
    fecha_gasto: datetime
    id_usuario: int
