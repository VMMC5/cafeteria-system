from sqlalchemy import Column, Integer, String, text

from app.db.base import Base


class Mesa(Base):
    __tablename__ = "mesas"

    id_mesa = Column(Integer, primary_key=True)
    numero_mesa = Column(Integer, nullable=False, unique=True)
    capacidad = Column(Integer, nullable=False)
    ubicacion = Column(String(50))
    estado = Column(String(20), nullable=False, server_default=text("'Disponible'"))
