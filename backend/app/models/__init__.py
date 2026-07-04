"""Modelos SQLAlchemy. Importar todo aquí para que Base.metadata los registre
(usado por Alembic autogenerate)."""

from app.models.compra import Compra, DetalleCompra, Proveedor
from app.models.configuracion import Configuracion
from app.models.gasto import CategoriaGasto, Gasto
from app.models.inventario import Insumo, MovimientoInventario, UnidadMedida
from app.models.mesa import Mesa
from app.models.pedido import Cancelacion, DetallePedido, EstadoPedido, Pedido
from app.models.producto import Categoria, Producto, ProductoInsumo
from app.models.usuario import Rol, Usuario
from app.models.venta import MetodoPago, Pago, Ticket, Venta

__all__ = [
    "Rol",
    "Usuario",
    "Mesa",
    "Categoria",
    "Producto",
    "ProductoInsumo",
    "UnidadMedida",
    "Insumo",
    "MovimientoInventario",
    "EstadoPedido",
    "Pedido",
    "DetallePedido",
    "Cancelacion",
    "MetodoPago",
    "Venta",
    "Ticket",
    "Pago",
    "Proveedor",
    "Compra",
    "DetalleCompra",
    "CategoriaGasto",
    "Gasto",
    "Configuracion",
]
