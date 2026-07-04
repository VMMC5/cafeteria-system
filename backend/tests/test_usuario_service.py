import pytest
from fastapi import HTTPException

from app.schemas.usuario import UsuarioCreate
from app.services import usuario_service


def _rol_id(db, nombre):
    from app.models import Rol

    return db.query(Rol).filter(Rol.nombre_rol == nombre).one().id_rol


def _payload(db, **over):
    base = dict(
        nombre="Ana",
        apellido_paterno="López",
        correo="ana@cafeteria.com",
        nombre_usuario="ana",
        id_rol=_rol_id(db, "Mesero"),
        password="secret123",
    )
    base.update(over)
    return UsuarioCreate(**base)


def test_create_y_authenticate(db):
    u = usuario_service.create_usuario(db, _payload(db))
    assert u.id_usuario is not None
    assert u.contrasena_hash != "secret123"
    assert usuario_service.authenticate(db, "ana@cafeteria.com", "secret123") is not None
    assert usuario_service.authenticate(db, "ana@cafeteria.com", "malo") is None


def test_create_correo_duplicado_409(db):
    usuario_service.create_usuario(db, _payload(db))
    with pytest.raises(HTTPException) as exc:
        usuario_service.create_usuario(db, _payload(db, nombre_usuario="otra"))
    assert exc.value.status_code == 409


def test_create_rol_inexistente_422(db):
    with pytest.raises(HTTPException) as exc:
        usuario_service.create_usuario(db, _payload(db, id_rol=99999))
    assert exc.value.status_code == 422


def test_soft_delete_desactiva(db):
    u = usuario_service.create_usuario(db, _payload(db))
    usuario_service.soft_delete(db, u.id_usuario, actor_id=-1)
    assert usuario_service.authenticate(db, "ana@cafeteria.com", "secret123") is None


def test_soft_delete_propia_cuenta_409(db):
    u = usuario_service.create_usuario(db, _payload(db))
    with pytest.raises(HTTPException) as exc:
        usuario_service.soft_delete(db, u.id_usuario, actor_id=u.id_usuario)
    assert exc.value.status_code == 409


def test_list_busqueda(db):
    usuario_service.create_usuario(db, _payload(db))
    encontrados = usuario_service.list_usuarios(db, q="ana")
    assert any(u.correo == "ana@cafeteria.com" for u in encontrados)
