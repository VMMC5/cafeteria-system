from app.db.seed import seed_catalogo
from app.models import Mesa, Producto


def test_seed_catalogo_crea_e_idempotente(db):
    seed_catalogo(db)
    assert db.query(Mesa).count() >= 10
    assert db.query(Producto).count() >= 7
    # idempotente
    creados = seed_catalogo(db)
    assert creados == 0
