import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import get_db
from app.main import app
from app.models import Rol, Usuario

engine = create_engine(settings.DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False)


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
