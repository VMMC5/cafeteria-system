from app.core.config import settings
from app.db.seed import seed_admin
from app.services import usuario_service


def test_seed_admin_idempotente_y_autentica(db):
    # Tolerante a la BD dev: si el admin ya existe, seed_admin no lo duplica.
    # (No se borra el admin: puede tener filas que lo referencian, p.ej. pedidos.)
    seed_admin(db)
    assert seed_admin(db) == 0  # idempotente: la segunda vez no crea
    user = usuario_service.authenticate(
        db, settings.ADMIN_CORREO, settings.ADMIN_PASSWORD
    )
    assert user is not None
