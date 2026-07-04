from sqlalchemy import Column, Integer, String

from app.db.base import Base


class Configuracion(Base):
    """Parámetros del sistema (clave-valor)."""

    __tablename__ = "configuracion"

    id_config = Column(Integer, primary_key=True)
    clave = Column(String(60), nullable=False, unique=True)
    valor = Column(String(255), nullable=False)
    descripcion = Column(String(150))
