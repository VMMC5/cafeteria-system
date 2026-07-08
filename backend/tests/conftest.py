import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.seed import seed_base
from app.db.session import get_db
from app.main import app
from app.models import Rol, Usuario


def _test_db_url() -> str:
    """URL de la BD de test: `TEST_DATABASE_URL` si está seteada, si no se
    deriva de `DATABASE_URL` cambiando el nombre de la base por `<nombre>_test`,
    para no tocar jamás la BD de desarrollo (donde vive la data demo del panel)."""
    if settings.TEST_DATABASE_URL:
        resolved = make_url(settings.TEST_DATABASE_URL)
    else:
        dev = make_url(settings.DATABASE_URL)
        resolved = dev.set(database=f"{dev.database}_test")
    # GUARDIA: la BD de test debe apuntar a una base ESTRICTAMENTE distinta de la
    # de dev. Si coincidieran (host+puerto+nombre), el `seed_base` de sesión
    # commitearía el baseline sobre la BD de dev y borraría/contaminaría la data
    # demo del panel. Fallar rápido y ruidoso antes de tocar nada.
    dev = make_url(settings.DATABASE_URL)
    if (resolved.host, resolved.port, resolved.database) == (
        dev.host,
        dev.port,
        dev.database,
    ):
        raise RuntimeError(
            "TEST_DATABASE_URL apunta a la MISMA base que DATABASE_URL "
            f"({dev.database!r} en {dev.host}:{dev.port}). La BD de test debe ser "
            "una base distinta para no dañar los datos de desarrollo."
        )
    # OJO: `str(url)` oculta la contraseña (hide_password=True por defecto);
    # hay que serializar explícitamente con la contraseña real o la conexión
    # a la BD de test falla por autenticación.
    return resolved.render_as_string(hide_password=False)


TEST_DATABASE_URL = _test_db_url()
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)


def _ensure_database_exists(url) -> None:
    """Crea la BD de test en el servidor si todavía no existe. Se conecta a la
    BD de mantenimiento `postgres` (nunca a la BD de dev) en modo AUTOCOMMIT,
    porque `CREATE DATABASE` no puede ejecutarse dentro de una transacción."""
    target = make_url(url)
    maintenance_url = target.set(database="postgres")
    maintenance_engine = create_engine(
        maintenance_url, isolation_level="AUTOCOMMIT"
    )
    try:
        with maintenance_engine.connect() as conn:
            existe = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": target.database},
            ).first()
            if not existe:
                conn.execute(text(f'CREATE DATABASE "{target.database}"'))
    finally:
        maintenance_engine.dispose()


@pytest.fixture(scope="session", autouse=True)
def _provision_test_database():
    """Fixture de sesión: garantiza que exista una BD de test dedicada, limpia,
    con el esquema completo y el baseline de `seed_base` (catálogos + admin +
    usuarios demo + mesas/productos), SIN datos transaccionales demo. Nunca
    toca la BD de dev: solo lee `DATABASE_URL` para derivar el nombre."""
    _ensure_database_exists(TEST_DATABASE_URL)

    # Esquema: create_all es autocontenido (no requiere correr Alembic dentro
    # de los tests) y refleja fielmente los modelos, incluidas las columnas
    # `Computed`/defaults definidas en ellos.
    Base.metadata.create_all(engine)

    session = Session(bind=engine)
    try:
        seed_base(session)
        session.commit()
    finally:
        session.close()

    yield

    engine.dispose()


@pytest.fixture()
def db():
    connection = engine.connect()
    trans = connection.begin()
    session = TestingSessionLocal(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    try:
        yield session
    finally:
        session.close()
        trans.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _rol_id(db, nombre):
    return db.query(Rol).filter(Rol.nombre_rol == nombre).one().id_rol


def _crear_usuario(db, nombre_usuario, correo, rol_nombre, password="secret123"):
    user = Usuario(
        nombre="Test",
        apellido_paterno="User",
        correo=correo,
        nombre_usuario=nombre_usuario,
        contrasena_hash=hash_password(password),
        id_rol=_rol_id(db, rol_nombre),
    )
    db.add(user)
    db.flush()
    return user


@pytest.fixture()
def admin(db):
    return _crear_usuario(db, "admintest", "admin.test@cafeteria.com", "Administrador")


@pytest.fixture()
def mesero(db):
    return _crear_usuario(db, "meserotest", "mesero.test@cafeteria.com", "Mesero")


def _headers(client, correo, password="secret123"):
    r = client.post(
        "/api/v1/auth/login", data={"username": correo, "password": password}
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client, admin):
    return _headers(client, "admin.test@cafeteria.com")


@pytest.fixture()
def mesero_headers(client, mesero):
    return _headers(client, "mesero.test@cafeteria.com")


@pytest.fixture()
def cocinero(db):
    return _crear_usuario(db, "cocinerotest", "cocinero.test@cafeteria.com", "Cocinero")


@pytest.fixture()
def cocinero_headers(client, cocinero):
    return _headers(client, "cocinero.test@cafeteria.com")


@pytest.fixture()
def cajero(db):
    return _crear_usuario(db, "cajerotest", "cajero.test@cafeteria.com", "Cajero")


@pytest.fixture()
def cajero_headers(client, cajero):
    return _headers(client, "cajero.test@cafeteria.com")
