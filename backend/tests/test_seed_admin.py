from app.core.config import settings
from app.db.seed import seed_admin
from app.models import Usuario
from app.services import usuario_service


def test_seed_admin_crea_e_idempotente(db):
    # Aislar de la BD dev (donde el admin puede ya existir); se revierte al final.
    db.query(Usuario).filter(Usuario.correo == settings.ADMIN_CORREO).delete()
    db.flush()

    creados = seed_admin(db)
    assert creados == 1
    assert seed_admin(db) == 0  # idempotente
    user = usuario_service.authenticate(
        db, settings.ADMIN_CORREO, settings.ADMIN_PASSWORD
    )
    assert user is not None
