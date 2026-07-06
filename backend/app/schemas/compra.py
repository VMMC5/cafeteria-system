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
