from app.core.config import settings
from app.db.seed import seed_admin
from app.models import Usuario
from app.services import usuario_service


def test_seed_admin_crea_autentica_y_es_idempotente(db):
    """Contrato de `seed_admin`: crea el admin desde .env si falta, no lo duplica
    en la segunda pasada, y el admin resultante autentica con esa credencial.

    El admin se borra ANTES, dentro de la transacción del test (que se revierte al
    terminar, así que la fila real sobrevive). Sin esto el test dependería del hash
    con que se sembró la BD de test: `seed_admin` no resincroniza la contraseña de
    un admin existente, así que si `ADMIN_PASSWORD` cambió en .env después de
    sembrarla, el hash guardado ya no corresponde y el test mediría el entorno en
    vez del código.
    """
    db.query(Usuario).filter(Usuario.correo == settings.ADMIN_CORREO).delete()
    db.flush()

    assert seed_admin(db) == 1  # crea el admin que falta
    assert seed_admin(db) == 0  # idempotente: la segunda vez no crea

    user = usuario_service.authenticate(
        db, settings.ADMIN_CORREO, settings.ADMIN_PASSWORD
    )
    assert user is not None
    assert user.rol.nombre_rol == "Administrador"
