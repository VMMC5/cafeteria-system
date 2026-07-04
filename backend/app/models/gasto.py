from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)

from app.db.base import Base


class CategoriaGasto(Base):
    __tablename__ = "categorias_gasto"

    id_categoria_gasto = Column(Integer, primary_key=True)
    nombre_categoria = Column(String(60), nullable=False)
    descripcion = Column(String(150))


class Gasto(Base):
    """Egresos generales no ligados a compra de insumos."""

    __tablename__ = "gastos"

    id_gasto = Column(Integer, primary_key=True)
    id_usuario = Column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )
    id_categoria_gasto = Column(
        Integer,
        ForeignKey("categorias_gasto.id_categoria_gasto"),
        nullable=False,
        index=True,
    )
    concepto = Column(String(150), nullable=False)
    monto = Column(Numeric(10, 2), nullable=False)
    fecha_gasto = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
