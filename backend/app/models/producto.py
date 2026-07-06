from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id_categoria = Column(Integer, primary_key=True)
    nombre_categoria = Column(String(60), nullable=False, unique=True)
    descripcion = Column(String(150))


class Producto(Base):
    __tablename__ = "productos"

    id_producto = Column(Integer, primary_key=True)
    id_categoria = Column(
        Integer, ForeignKey("categorias.id_categoria"), nullable=False, index=True
    )
    nombre_producto = Column(String(100), nullable=False)
    descripcion = Column(String(255))
    precio_venta = Column(Numeric(10, 2), nullable=False)
    disponible = Column(Boolean, nullable=False, server_default=text("true"))
    fecha_registro = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    categoria = relationship("Categoria", lazy="joined")


class ProductoInsumo(Base):
    """Receta (N:M producto-insumo). Base del descuento automático de stock."""

    __tablename__ = "producto_insumo"

    id_producto_insumo = Column(Integer, primary_key=True)
    id_producto = Column(
        Integer, ForeignKey("productos.id_producto"), nullable=False, index=True
    )
    id_insumo = Column(
        Integer, ForeignKey("insumos.id_insumo"), nullable=False, index=True
    )
    cantidad_requerida = Column(Numeric(10, 3), nullable=False)

    insumo = relationship("Insumo", lazy="joined")
