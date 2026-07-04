from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    func,
    text,
)

from app.db.base import Base


class MetodoPago(Base):
    __tablename__ = "metodos_pago"

    id_metodo_pago = Column(Integer, primary_key=True)
    nombre_metodo = Column(String(30), nullable=False)
    descripcion = Column(String(150))


class Venta(Base):
    """Registro financiero del cobro de un pedido (1:1, inmutable)."""

    __tablename__ = "ventas"

    id_venta = Column(Integer, primary_key=True)
    id_pedido = Column(
        Integer, ForeignKey("pedidos.id_pedido"), nullable=False, unique=True
    )
    id_usuario = Column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )
    fecha_venta = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    total = Column(Numeric(12, 2), nullable=False)
    estado_venta = Column(
        String(20), nullable=False, server_default=text("'Completada'")
    )


class Ticket(Base):
    __tablename__ = "tickets"

    id_ticket = Column(Integer, primary_key=True)
    id_venta = Column(
        Integer, ForeignKey("ventas.id_venta"), nullable=False, unique=True
    )
    folio = Column(String(30), nullable=False, unique=True)
    fecha_emision = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Pago(Base):
    """Pagos aplicados a una venta (1:N). Soporta pago dividido."""

    __tablename__ = "pagos"

    id_pago = Column(Integer, primary_key=True)
    id_venta = Column(Integer, ForeignKey("ventas.id_venta"), nullable=False, index=True)
    id_metodo_pago = Column(
        Integer, ForeignKey("metodos_pago.id_metodo_pago"), nullable=False, index=True
    )
    monto = Column(Numeric(10, 2), nullable=False)
    referencia = Column(String(100))
    fecha_pago = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
