from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.categoria import CategoriaOut


class ProductoCreate(BaseModel):
    id_categoria: int
    nombre_producto: str
    descripcion: str | None = None
    precio_venta: Decimal = Field(ge=0)
    disponible: bool = True


class ProductoUpdate(BaseModel):
    id_categoria: int | None = None
    nombre_producto: str | None = None
    descripcion: str | None = None
    precio_venta: Decimal | None = Field(default=None, ge=0)
    disponible: bool | None = None


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    id_categoria: int
    nombre_producto: str
    descripcion: str | None
    precio_venta: Decimal
    disponible: bool
    fecha_registro: datetime
    categoria: CategoriaOut
