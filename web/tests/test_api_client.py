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
