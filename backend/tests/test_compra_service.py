from decimal import Decimal

from app.services.compra_service import _costo_promedio


def test_promedio_ponderado_redondea_half_up():
    # 10 kg @ $95 + 8 kg @ $98.50 = $1738 / 18 = $96.5555… → $96.56
    r = _costo_promedio(
        Decimal("10"), Decimal("95.00"), Decimal("8"), Decimal("98.50")
    )
    assert r == Decimal("96.56")


def test_promedio_redondea_hacia_abajo_bajo_medio_centavo():
    # 10 @ $95 + 5 @ $95.10 = $1425.50 / 15 = $95.0333… → $95.03
    r = _costo_promedio(
        Decimal("10"), Decimal("95.00"), Decimal("5"), Decimal("95.10")
    )
    assert r == Decimal("95.03")


def test_stock_cero_toma_el_costo_de_la_compra():
    r = _costo_promedio(Decimal("0"), Decimal("95.00"), Decimal("8"), Decimal("98.50"))
    assert r == Decimal("98.50")


def test_costo_cero_toma_el_costo_de_la_compra():
    """Promediar contra stock valuado a $0 diluiría el costo con unidades que
    nadie pagó (10 pzas a $0 + 5 a $30 daría $10)."""
    r = _costo_promedio(Decimal("10"), Decimal("0"), Decimal("5"), Decimal("30.00"))
    assert r == Decimal("30.00")


def test_composicion_secuencial_dos_lineas():
    """Una compra con el mismo insumo en dos líneas promedia en cadena: la
    segunda línea parte del costo y stock resultantes de la primera."""
    paso1 = _costo_promedio(
        Decimal("10"), Decimal("95.00"), Decimal("8"), Decimal("98.50")
    )  # 96.56, stock queda en 18
    paso2 = _costo_promedio(Decimal("18"), paso1, Decimal("2"), Decimal("100.00"))
    # (18 × 96.56 + 2 × 100) / 20 = 1938.08 / 20 = 96.904 → 96.90
    assert paso2 == Decimal("96.90")


def test_stock_fraccionario_tres_decimales():
    """El stock es Numeric(10,3) desde el PR #26: el promedio opera con
    cantidades fraccionarias exactas."""
    # 0.500 kg @ $80 + 0.250 kg @ $92 = 40 + 23 = 63 / 0.75 = 84
    r = _costo_promedio(
        Decimal("0.500"), Decimal("80.00"), Decimal("0.250"), Decimal("92.00")
    )
    assert r == Decimal("84.00")
