from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EstadoMesa = Literal["Disponible", "Ocupada", "Reservada"]


class MesaCreate(BaseModel):
    numero_mesa: int
    capacidad: int = Field(ge=1)
    ubicacion: str | None = None
    estado: EstadoMesa = "Disponible"


class MesaUpdate(BaseModel):
    numero_mesa: int | None = None
    capacidad: int | None = Field(default=None, ge=1)
    ubicacion: str | None = None
    estado: EstadoMesa | None = None


class MesaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_mesa: int
    numero_mesa: int
    capacidad: int
    ubicacion: str | None
    estado: str
