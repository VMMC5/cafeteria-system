from decimal import Decimal

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


class EstadoPedido(Base):
    __tablename__ = "estados_pedido"

    id_estado = Column(Integer, primary_key=True)
    nombre_estado = Column(String(30), nullable=False)
    descripcion = Column(String(150))


class Pedido(Base):
    __tablename__ = "pedidos"

    id_pedido = Column(Integer, primary_key=True)
    id_mesa = Column(Integer, ForeignKey("mesas.id_mesa"), nullable=False, index=True)
    id_usuario = Column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )
    id_estado = Column(
        Integer, ForeignKey("estados_pedido.id_estado"), nullable=False, index=True
    )
    fecha_pedido = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    observaciones = Column(String(255))

    mesa = relationship("Mesa", lazy="joined")
    estado = relationship("EstadoPedido", lazy="joined")
    detalle = relationship(
        "DetallePedido", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def total(self) -> Decimal:
        return sum((d.subtotal for d in self.detalle), Decimal("0"))


class DetallePedido(Base):
    __tablename__ = "detalle_pedido"

    id_detalle = Column(Integer, primary_key=True)
    id_pedido = Column(
        Integer, ForeignKey("pedidos.id_pedido"), nullable=False, index=True
    )
    id_producto = Column(
        Integer, ForeignKey("productos.id_producto"), nullable=False, index=True
    )
    cantidad = Column(Integer, nullable=False)
    precio_unitario = Column(Numeric(10, 2), nullable=False)
    subtotal = Column(
        Numeric(12, 2), Computed("cantidad * precio_unitario", persisted=True)
    )
    observaciones = Column(String(255))

    producto = relationship("Producto", lazy="joined")


class Cancelacion(Base):
    """Bitácora de cancelaciones (1:0..1 con pedidos)."""

    __tablename__ = "cancelaciones"

    id_cancelacion = Column(Integer, primary_key=True)
    id_pedido = Column(
        Integer, ForeignKey("pedidos.id_pedido"), nullable=False, unique=True
    )
    id_usuario = Column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )
    motivo = Column(String(255), nullable=False)
    fecha_cancelacion = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
