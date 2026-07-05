from pydantic import BaseModel, ConfigDict


class EstadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_estado: int
    nombre_estado: str
