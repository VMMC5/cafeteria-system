from sqlalchemy import (
    Column,
    Computed,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id_proveedor = Column(Integer, primary_key=True)
    nombre_proveedor = Column(String(120), nullable=False)
    telefono = Column(String(20))
    correo = Column(String(150))
    direccion = Column(String(255))


class Compra(Base):
    __tablename__ = "compras"

    id_compra = Column(Integer, primary_key=True)
    id_proveedor = Column(
        Integer, ForeignKey("proveedores.id_proveedor"), nullable=False, index=True
    )
    id_usuario = Column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )
    fecha_compra = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    total = Column(Numeric(12, 2), nullable=False)
    folio_factura = Column(String(50))

    proveedor = relationship("Proveedor", lazy="joined")
    detalle = relationship("DetalleCompra", lazy="selectin")


class DetalleCompra(Base):
    __tablename__ = "detalle_compra"

    id_detalle_compra = Column(Integer, primary_key=True)
    id_compra = Column(
        Integer, ForeignKey("compras.id_compra"), nullable=False, index=True
    )
    id_insumo = Column(
        Integer, ForeignKey("insumos.id_insumo"), nullable=False, index=True
    )
    cantidad = Column(Numeric(10, 2), nullable=False)
    costo_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(
        Numeric(12, 2), Computed("cantidad * costo_unitario", persisted=True)
    )

    insumo = relationship("Insumo", lazy="joined")
