import pytest
from pydantic import ValidationError

from app.schemas.usuario import UsuarioCreate, UsuarioOut


def _datos_validos(**over):
    base = dict(
        nombre="Ana",
        apellido_paterno="López",
        correo="ana@caf.local",
        nombre_usuario="ana",
        id_rol=1,
        password="secret123",
    )
    base.update(over)
    return base


def test_usuario_create_password_corta_falla():
    with pytest.raises(ValidationError):
        UsuarioCreate(**_datos_validos(password="123"))


def test_usuario_create_correo_invalido_falla():
    with pytest.raises(ValidationError):
        UsuarioCreate(**_datos_validos(correo="no-es-correo"))


def test_usuario_out_no_expone_hash():
    assert "contrasena_hash" not in UsuarioOut.model_fields
