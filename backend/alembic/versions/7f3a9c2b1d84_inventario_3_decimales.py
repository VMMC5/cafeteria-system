"""inventario a 3 decimales

Revision ID: 7f3a9c2b1d84
Revises: a1557e1dd3bf
Create Date: 2026-08-09

Amplía las cuatro columnas de cantidad del inventario de Numeric(10,2) a
Numeric(10,3), para que el stock y el kárdex representen exactamente lo que
consume una receta (`producto_insumo.cantidad_requerida` siempre fue (10,3)).
El dinero se queda en 2 decimales.

OJO 1 — detalle_compra.subtotal es una columna GENERADA que depende de
`cantidad`, y Postgres rechaza alterar el tipo de una columna de la que
depende una generada ("cannot alter type of a column used by a generated
column"). Hay que eliminarla, alterar `cantidad` y volver a crearla; Postgres
recalcula la columna generada para las filas existentes, así que no se pierde
nada.

OJO 2 — el downgrade REDONDEA el tercer decimal y esa pérdida es
irreversible: un stock de 0.125 vuelve como 0.13.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f3a9c2b1d84"
down_revision: Union[str, Sequence[str], None] = "a1557e1dd3bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_GEN_SUBTOTAL = "cantidad * costo_unitario"


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "insumos", "stock_actual",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "insumos", "stock_minimo",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "movimientos_inventario", "cantidad",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False,
    )
    # detalle_compra: la columna generada bloquea el ALTER, hay que recrearla.
    op.drop_column("detalle_compra", "subtotal")
    op.alter_column(
        "detalle_compra", "cantidad",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False,
    )
    op.add_column(
        "detalle_compra",
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            sa.Computed(_GEN_SUBTOTAL, persisted=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema. PIERDE el tercer decimal por redondeo."""
    op.drop_column("detalle_compra", "subtotal")
    op.alter_column(
        "detalle_compra", "cantidad",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False,
    )
    op.add_column(
        "detalle_compra",
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            sa.Computed(_GEN_SUBTOTAL, persisted=True),
            nullable=True,
        ),
    )
    op.alter_column(
        "movimientos_inventario", "cantidad",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "insumos", "stock_minimo",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "insumos", "stock_actual",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
