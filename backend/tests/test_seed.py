import app.db.seed as seed_mod
from app.core.security import verify_password
from app.db.seed import DEMO_PASSWORD, seed_usuarios_demo
from app.models import Rol, Usuario

REALES = [
    ("mesero@cafeteria.com", "Mesero"),
    ("cajero@cafeteria.com", "Cajero"),
    ("cocinero@cafeteria.com", "Cocinero"),
]


def _rol_de(db, correo):
    u = db.query(Usuario).filter(Usuario.correo == correo).one()
    return db.get(Rol, u.id_rol).nombre_rol


def test_seed_usuarios_demo_crea_con_rol_password_e_idempotente(db, monkeypatch):
    # Usuario ficticio que no existe en la BD, para probar la creación en aislado.
    fake = [("Demo", "Prueba", "demo.seed.test@cafeteria.com", "demo_seed_test", "Mesero")]
    monkeypatch.setattr(seed_mod, "USUARIOS_DEMO", fake)

    assert seed_usuarios_demo(db) == 1
    u = db.query(Usuario).filter(Usuario.correo == "demo.seed.test@cafeteria.com").one()
    assert db.get(Rol, u.id_rol).nombre_rol == "Mesero"
    assert verify_password(DEMO_PASSWORD, u.contrasena_hash)

    # Segunda llamada: no duplica.
    assert seed_usuarios_demo(db) == 0
    assert (
        db.query(Usuario)
        .filter(Usuario.correo == "demo.seed.test@cafeteria.com")
        .count()
        == 1
    )


def test_seed_usuarios_demo_correos_y_roles_reales(db):
    seed_usuarios_demo(db)
    for correo, rol in REALES:
        assert db.query(Usuario).filter(Usuario.correo == correo).count() == 1
        assert _rol_de(db, correo) == rol


def test_seed_admin_corrige_rol_incorrecto(db):
    from app.core.config import settings
    from app.db.seed import seed_admin

    admin = db.query(Usuario).filter(Usuario.correo == settings.ADMIN_CORREO).one()
    admin_rol = db.query(Rol).filter(Rol.nombre_rol == "Administrador").one().id_rol
    cajero = db.query(Rol).filter(Rol.nombre_rol == "Cajero").one().id_rol

    admin.id_rol = cajero
    db.flush()
    assert seed_admin(db) == 1  # corrige
    db.refresh(admin)
    assert admin.id_rol == admin_rol
