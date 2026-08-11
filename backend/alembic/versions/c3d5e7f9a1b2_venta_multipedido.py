"""venta multi-pedido: la FK se invierte a pedidos.id_venta

Revision ID: c3d5e7f9a1b2
Revises: 7f3a9c2b1d84
Create Date: 2026-08-11

"""
import sqlalchemy as sa
from alembic import op

revision = "c3d5e7f9a1b2"
down_revision = "7f3a9c2b1d84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pedidos", sa.Column("id_venta", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "pedidos_id_venta_fkey", "pedidos", "ventas", ["id_venta"], ["id_venta"]
    )
    op.create_index("ix_pedidos_id_venta", "pedidos", ["id_venta"])
    # Backfill: cada venta existente (1:1) marca a su pedido.
    op.execute(
        "UPDATE pedidos SET id_venta = v.id_venta "
        "FROM ventas v WHERE v.id_pedido = pedidos.id_pedido"
    )
    # Postgres elimina en cascada el unique y la FK que cuelgan de la columna.
    op.drop_column("ventas", "id_pedido")


def downgrade() -> None:
    # Parcial: una venta multi-pedido conserva solo su primera ronda (mismo
    # criterio de irreversibilidad aceptado en 7f3a9c2b1d84).
    op.add_column("ventas", sa.Column("id_pedido", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE ventas SET id_pedido = ("
        "SELECT MIN(p.id_pedido) FROM pedidos p WHERE p.id_venta = ventas.id_venta)"
    )
    op.alter_column("ventas", "id_pedido", nullable=False)
    op.create_foreign_key(
        "ventas_id_pedido_fkey", "ventas", "pedidos", ["id_pedido"], ["id_pedido"]
    )
    op.create_unique_constraint("ventas_id_pedido_key", "ventas", ["id_pedido"])
    op.drop_index("ix_pedidos_id_venta", table_name="pedidos")
    op.drop_column("pedidos", "id_venta")
