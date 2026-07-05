from decimal import Decimal

from app.services.venta_service import desglose


def test_desglose_iva_incluido():
    base, iva = desglose(Decimal("116"), Decimal("0.16"))
    assert base == Decimal("100.00")
    assert iva == Decimal("16.00")


def test_desglose_redondea_a_centavos():
    base, iva = desglose(Decimal("100"), Decimal("0.16"))
    assert base == Decimal("86.21")
    assert iva == Decimal("13.79")
