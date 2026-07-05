from pydantic import BaseModel, ConfigDict


class CategoriaCreate(BaseModel):
    nombre_categoria: str
    descripcion: str | None = None


class CategoriaUpdate(BaseModel):
    nombre_categoria: str | None = None
    descripcion: str | None = None


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: int
    nombre_categoria: str
    descripcion: str | None
