from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    func,
    text,
)

from app.db.base import Base


class Rol(Base):
    __tablename__ = "roles"

    id_rol = Column(Integer, primary_key=True)
    nombre_rol = Column(String(50), nullable=False, unique=True)
    descripcion = Column(String(150))


class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario = Column(Integer, primary_key=True)
    id_rol = Column(Integer, ForeignKey("roles.id_rol"), nullable=False, index=True)
    nombre = Column(String(60), nullable=False)
    apellido_paterno = Column(String(60), nullable=False)
    apellido_materno = Column(String(60))
    correo = Column(String(150), nullable=False, unique=True)
    nombre_usuario = Column(String(50), nullable=False, unique=True)
    contrasena_hash = Column(String(255), nullable=False)
    activo = Column(Boolean, nullable=False, server_default=text("true"))
    fecha_registro = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
