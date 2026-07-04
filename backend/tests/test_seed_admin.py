from app.core.config import settings
from app.db.seed import seed_admin
from app.services import usuario_service


def test_seed_admin_crea_e_idempotente(db):
    creados = seed_admin(db)
    assert creados == 1
    assert seed_admin(db) == 0  # idempotente
    user = usuario_service.authenticate(
        db, settings.ADMIN_CORREO, settings.ADMIN_PASSWORD
    )
    assert user is not None
