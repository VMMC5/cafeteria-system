import pytest

from app.services import api_client
from app.services.api_client import ApiError


class _Resp:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_login_ok(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["data"] = kwargs.get("data")
        return _Resp(200, {"access_token": "a", "refresh_token": "r", "token_type": "bearer"})

    monkeypatch.setattr(api_client.requests, "post", fake_post)
    out = api_client.login("admin@cafeteria.com", "secret123")
    assert out["access_token"] == "a"
    assert captured["url"].endswith("/auth/login")
    assert captured["data"] == {"username": "admin@cafeteria.com", "password": "secret123"}


def test_login_401_lanza_apierror(monkeypatch):
    monkeypatch.setattr(
        api_client.requests, "post", lambda url, **k: _Resp(401, {"detail": "malo"})
    )
    with pytest.raises(ApiError) as exc:
        api_client.login("x@y.com", "z")
    assert exc.value.status_code == 401


def test_list_usuarios_manda_bearer(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["headers"] = kwargs.get("headers")
        captured["params"] = kwargs.get("params")
        return _Resp(200, [{"id_usuario": 1}])

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    out = api_client.list_usuarios("tok", q="ana")
    assert out == [{"id_usuario": 1}]
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert captured["params"] == {"q": "ana"}


def test_list_productos_filtra_params(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["params"] = kwargs.get("params")
        return _Resp(200, [{"id_producto": 1, "precio_venta": "45.00"}])

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    out = api_client.list_productos("tok", id_categoria=2, disponible=True)
    assert out[0]["precio_venta"] == "45.00"
    assert captured["url"].endswith("/productos")
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert captured["params"] == {"id_categoria": 2, "disponible": True}


def test_list_productos_sin_filtros_no_manda_params(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["params"] = kwargs.get("params")
        return _Resp(200, [])

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    api_client.list_productos("tok")
    assert captured["params"] is None


def test_create_producto_postea_json(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _Resp(201, {"id_producto": 7})

    monkeypatch.setattr(api_client.requests, "post", fake_post)
    out = api_client.create_producto(
        "tok", {"nombre_producto": "Latte", "precio_venta": "45.00"}
    )
    assert out == {"id_producto": 7}
    assert captured["url"].endswith("/productos")
    assert captured["json"]["precio_venta"] == "45.00"


def test_delete_mesa_204_devuelve_none(monkeypatch):
    captured = {}

    def fake_delete(url, **kwargs):
        captured["url"] = url
        return _Resp(204)

    monkeypatch.setattr(api_client.requests, "delete", fake_delete)
    assert api_client.delete_mesa("tok", 3) is None
    assert captured["url"].endswith("/mesas/3")


def test_delete_categoria_con_referencias_lanza_apierror(monkeypatch):
    monkeypatch.setattr(
        api_client.requests, "delete",
        lambda url, **k: _Resp(409, {"detail": "La categoría tiene productos"}),
    )
    with pytest.raises(ApiError) as exc:
        api_client.delete_categoria("tok", 2)
    assert exc.value.status_code == 409
