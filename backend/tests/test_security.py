import pytest
from jose import JWTError

from app.core import security


def test_hash_y_verify_password():
    hashed = security.hash_password("secret123")
    assert hashed != "secret123"
    assert security.verify_password("secret123", hashed) is True
    assert security.verify_password("malo", hashed) is False


def test_access_token_roundtrip():
    token = security.create_access_token(sub="7", rol="Administrador")
    payload = security.decode_token(token)
    assert payload["sub"] == "7"
    assert payload["rol"] == "Administrador"
    assert payload["type"] == "access"


def test_refresh_token_tiene_type_refresh():
    token = security.create_refresh_token(sub="7")
    payload = security.decode_token(token)
    assert payload["type"] == "refresh"
    assert "rol" not in payload


def test_decode_token_invalido_lanza():
    with pytest.raises(JWTError):
        security.decode_token("no.es.un.jwt")
