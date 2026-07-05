def _nuevo(db):
    from app.models import Rol

    id_rol = db.query(Rol).filter(Rol.nombre_rol == "Mesero").one().id_rol
    return {
        "nombre": "Beto",
        "apellido_paterno": "Ruiz",
        "correo": "beto@cafeteria.com",
        "nombre_usuario": "beto",
        "id_rol": id_rol,
        "password": "secret123",
    }


def test_listar_requiere_admin(client, mesero_headers):
    assert client.get("/api/v1/usuarios", headers=mesero_headers).status_code == 403


def test_listar_sin_token_401(client):
    assert client.get("/api/v1/usuarios").status_code == 401


def test_crear_y_listar(client, db, admin_headers):
    r = client.post("/api/v1/usuarios", headers=admin_headers, json=_nuevo(db))
    assert r.status_code == 201
    assert "contrasena_hash" not in r.json()
    r2 = client.get("/api/v1/usuarios?q=beto", headers=admin_headers)
    assert any(u["correo"] == "beto@cafeteria.com" for u in r2.json())


def test_crear_correo_duplicado_409(client, db, admin_headers):
    client.post("/api/v1/usuarios", headers=admin_headers, json=_nuevo(db))
    dup = _nuevo(db)
    dup["nombre_usuario"] = "otro"
    assert (
        client.post("/api/v1/usuarios", headers=admin_headers, json=dup).status_code
        == 409
    )


def test_patch_desactiva(client, db, admin_headers):
    creado = client.post(
        "/api/v1/usuarios", headers=admin_headers, json=_nuevo(db)
    ).json()
    r = client.patch(
        f"/api/v1/usuarios/{creado['id_usuario']}",
        headers=admin_headers,
        json={"activo": False},
    )
    assert r.status_code == 200 and r.json()["activo"] is False


def test_delete_soft(client, db, admin_headers):
    creado = client.post(
        "/api/v1/usuarios", headers=admin_headers, json=_nuevo(db)
    ).json()
    r = client.delete(
        f"/api/v1/usuarios/{creado['id_usuario']}", headers=admin_headers
    )
    assert r.status_code == 200 and r.json()["activo"] is False


def test_admin_no_se_autodesactiva(client, admin, admin_headers):
    r = client.delete(
        f"/api/v1/usuarios/{admin.id_usuario}", headers=admin_headers
    )
    assert r.status_code == 409


def test_crear_devuelve_rol_anidado(client, db, admin_headers):
    r = client.post("/api/v1/usuarios", headers=admin_headers, json=_nuevo(db))
    assert r.status_code == 201
    assert r.json()["rol"]["nombre_rol"] == "Mesero"
