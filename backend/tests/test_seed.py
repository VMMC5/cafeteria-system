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


def test_seed_base_sobre_bd_vacia(db):
    """`seed_base` debe funcionar sobre una BD totalmente vacía — el caso de un
    despliegue fresco (`alembic upgrade head` + `python -m app.db.seed`).

    Regresión: `SessionLocal` usa autoflush=False, y `seed_admin` consultaba los
    roles que el bucle de catálogos acababa de añadir a la sesión SIN flush
    previo: sobre una BD vacía la consulta no los veía y el seed moría con
    NoResultFound. Nunca se notó porque el seed siempre había corrido sobre una
    BD ya sembrada. Este fixture (`TestingSessionLocal`) comparte el
    autoflush=False de la app, así que reproduce el bug fielmente; los DELETE
    ocurren dentro de la transacción del fixture y se revierten al salir.
    """
    from app.core.config import settings
    from app.models import (
        Categoria,
        CategoriaGasto,
        Configuracion,
        EstadoPedido,
        Mesa,
        MetodoPago,
        Producto,
        Proveedor,
        UnidadMedida,
    )
    from app.db.seed import seed_base

    # Vaciar en orden FK-seguro (primero quien referencia, luego el catálogo).
    for modelo in (
        Producto, Usuario, Mesa, Proveedor, Configuracion, CategoriaGasto,
        UnidadMedida, Categoria, MetodoPago, EstadoPedido, Rol,
    ):
        db.query(modelo).delete()

    total = seed_base(db)

    assert total > 0
    assert db.query(Rol).count() == 4
    admin = db.query(Usuario).filter(Usuario.correo == settings.ADMIN_CORREO).one()
    assert db.get(Rol, admin.id_rol).nombre_rol == "Administrador"
