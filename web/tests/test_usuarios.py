from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
ROLES = [
    {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
    {"id_rol": 4, "nombre_rol": "Mesero", "descripcion": None},
]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "secret123"})


def test_form_nuevo_muestra_roles(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_roles", lambda a: ROLES)
    r = client.get("/usuarios/nuevo")
    assert r.status_code == 200
    assert b"Mesero" in r.data


def test_crear_ok_redirige(client, monkeypatch):
    _login(client, monkeypatch)
    capturado = {}

    def fake_create(access, payload):
        capturado["payload"] = payload
        return {"id_usuario": 9, **payload}

    monkeypatch.setattr(api_client, "create_usuario", fake_create)
    r = client.post("/usuarios", data={
        "nombre": "Beto", "apellido_paterno": "Ruiz", "apellido_materno": "",
        "correo": "beto@cafeteria.com", "nombre_usuario": "beto",
        "id_rol": "4", "password": "secret123",
    })
    assert r.status_code == 302
    assert "/usuarios" in r.headers["Location"]
    assert capturado["payload"]["correo"] == "beto@cafeteria.com"
    assert capturado["payload"]["id_rol"] == 4
    assert capturado["payload"]["apellido_materno"] is None


def test_crear_correo_duplicado_muestra_error(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_create(access, payload):
        raise ApiError(409, "El correo ya está registrado")

    monkeypatch.setattr(api_client, "create_usuario", fake_create)
    monkeypatch.setattr(api_client, "list_roles", lambda a: ROLES)
    r = client.post("/usuarios", data={
        "nombre": "Beto", "apellido_paterno": "Ruiz", "apellido_materno": "",
        "correo": "dup@cafeteria.com", "nombre_usuario": "beto",
        "id_rol": "4", "password": "secret123",
    })
    assert r.status_code == 409
    assert "registrado" in r.get_data(as_text=True)


def test_desactivar_llama_api(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}
    monkeypatch.setattr(
        api_client, "delete_usuario",
        lambda a, i: llamado.setdefault("id", i) or {"id_usuario": i, "activo": False},
    )
    r = client.post("/usuarios/5/desactivar")
    assert r.status_code == 302
    assert llamado["id"] == 5
