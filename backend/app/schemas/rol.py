from pydantic import BaseModel, ConfigDict


class RolOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_rol: int
    nombre_rol: str
    descripcion: str | None
