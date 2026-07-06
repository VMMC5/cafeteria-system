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
