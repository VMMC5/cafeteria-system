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


class UnidadMedida(Base):
    __tablename__ = "unidades_medida"

    id_unidad = Column(Integer, primary_key=True)
    nombre_unidad = Column(String(30), nullable=False)
    abreviatura = Column(String(10), nullable=False)


class Insumo(Base):
    __tablename__ = "insumos"

    id_insumo = Column(Integer, primary_key=True)
    id_unidad = Column(
        Integer, ForeignKey("unidades_medida.id_unidad"), nullable=False, index=True
    )
    nombre_insumo = Column(String(100), nullable=False)
    descripcion = Column(String(255))
    stock_actual = Column(Numeric(10, 2), nullable=False, server_default=text("0"))
    stock_minimo = Column(Numeric(10, 2), nullable=False, server_default=text("0"))
    costo_unitario = Column(Numeric(10, 2), nullable=False, server_default=text("0"))
    fecha_registro = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MovimientoInventario(Base):
    """Kárdex: bitácora de entradas/salidas de stock con su origen."""

    __tablename__ = "movimientos_inventario"

    id_movimiento = Column(Integer, primary_key=True)
    id_insumo = Column(
        Integer, ForeignKey("insumos.id_insumo"), nullable=False, index=True
    )
    id_usuario = Column(
        Integer, ForeignKey("usuarios.id_usuario"), nullable=False, index=True
    )
    id_pedido = Column(Integer, ForeignKey("pedidos.id_pedido"), index=True)
    id_compra = Column(Integer, ForeignKey("compras.id_compra"), index=True)
    tipo_movimiento = Column(String(10), nullable=False)  # Entrada / Salida
    motivo = Column(String(30), nullable=False)  # Compra, Venta, Ajuste, Merma, Inicial
    cantidad = Column(Numeric(10, 2), nullable=False)
    fecha_movimiento = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
