from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.rol import RolOut


class UsuarioCreate(BaseModel):
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None = None
    correo: EmailStr
    nombre_usuario: str
    id_rol: int
    password: str = Field(min_length=8)


class UsuarioUpdate(BaseModel):
    nombre: str | None = None
    apellido_paterno: str | None = None
    apellido_materno: str | None = None
    correo: EmailStr | None = None
    nombre_usuario: str | None = None
    id_rol: int | None = None
    password: str | None = Field(default=None, min_length=8)
    activo: bool | None = None


class UsuarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    nombre: str
    apellido_paterno: str
    apellido_materno: str | None
    correo: EmailStr
    nombre_usuario: str
    id_rol: int
    rol: RolOut
    activo: bool
    fecha_registro: datetime
