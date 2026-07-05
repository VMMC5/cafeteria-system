from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Configuracion

_IVA_DEFAULT = Decimal("0.16")


def _iva_tasa(db: Session) -> Decimal:
    row = db.execute(
        select(Configuracion).where(Configuracion.clave == "iva_tasa")
    ).scalar_one_or_none()
    return Decimal(row.valor) if row else _IVA_DEFAULT


def desglose(total: Decimal, tasa: Decimal) -> tuple[Decimal, Decimal]:
    base = (total / (Decimal("1") + tasa)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    iva = total - base
    return base, iva
