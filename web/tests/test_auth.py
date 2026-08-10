import pytest

from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
MESERO_ME = {**ADMIN_ME, "rol": {"id_rol": 4, "nombre_rol": "Mesero", "descripcion": None}}


def test_get_login_ok(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert b"Iniciar" in r.data or b"iniciar" in r.data


def test_login_admin_redirige(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    r = client.post(
        "/login", data={"correo": "admin@cafeteria.com", "password": "secret123"}
    )
    assert r.status_code == 302
    assert "/usuarios" in r.headers["Location"]


def test_login_no_admin_rechazado(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: MESERO_ME)
    r = client.post(
        "/login", data={"correo": "mesero@cafeteria.com", "password": "secret123"}
    )
    assert r.status_code == 403
    assert "administrador" in r.get_data(as_text=True).lower()


def test_login_credenciales_malas(client, monkeypatch):
    from app.services.api_client import ApiError

    def _bad(c, p):
        raise ApiError(401, "malo")

    monkeypatch.setattr(api_client, "login", _bad)
    r = client.post("/login", data={"correo": "x@y.com", "password": "z"})
    assert r.status_code == 401
    assert "incorrect" in r.get_data(as_text=True).lower()


def test_usuarios_sin_sesion_redirige(client):
    r = client.get("/usuarios")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "secret123"})


def test_usuarios_lista_renderiza(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(
        api_client,
        "list_usuarios",
        lambda a, q=None: [
            {"id_usuario": 1, "nombre": "Ana", "apellido_paterno": "López",
             "correo": "ana@cafeteria.com", "activo": True,
             "rol": {"nombre_rol": "Mesero"}}
        ],
    )
    r = client.get("/usuarios")
    assert r.status_code == 200
    assert b"Ana" in r.data
    assert b"Mesero" in r.data


def _login_admin(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "secret123"})


def test_logout_por_post_cierra_sesion(client, monkeypatch):
    _login_admin(client, monkeypatch)
    r = client.post("/logout")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]
    # La sesión quedó cerrada: una página protegida vuelve a redirigir al login.
    r2 = client.get("/usuarios")
    assert r2.status_code == 302
    assert "/login" in r2.headers["Location"]


def test_logout_por_get_405(client, monkeypatch):
    """El logout por GET era vulnerable a CSRF (un <img src=/logout> cerraba la
    sesión del admin). La ruta ya solo acepta POST."""
    _login_admin(client, monkeypatch)
    r = client.get("/logout")
    assert r.status_code == 405
    # Y la sesión sigue viva: la página protegida carga (no redirige a login).
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: [])
    assert client.get("/usuarios").status_code == 200
