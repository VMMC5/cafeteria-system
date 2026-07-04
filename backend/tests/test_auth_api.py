from app.core.security import create_refresh_token


def test_login_ok(client, admin):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin.test@cafeteria.com", "password": "secret123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_login_credenciales_malas(client, admin):
    r = client.post(
        "/api/v1/auth/login",
        data={"username": "admin.test@cafeteria.com", "password": "malo"},
    )
    assert r.status_code == 401


def test_me_con_token(client, admin_headers):
    r = client.get("/api/v1/auth/me", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["correo"] == "admin.test@cafeteria.com"
    assert "contrasena_hash" not in r.json()


def test_me_sin_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_refresh_rota_tokens(client, admin):
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin.test@cafeteria.com", "password": "secret123"},
    ).json()
    r = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["refresh_token"]}
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_refresh_con_access_token_falla(client, admin):
    login = client.post(
        "/api/v1/auth/login",
        data={"username": "admin.test@cafeteria.com", "password": "secret123"},
    ).json()
    r = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": login["access_token"]}
    )
    assert r.status_code == 401


def test_refresh_usuario_desactivado_falla(client, db, admin):
    token = create_refresh_token(str(admin.id_usuario))
    admin.activo = False
    db.flush()
    r = client.post("/api/v1/auth/refresh", json={"refresh_token": token})
    assert r.status_code == 401
