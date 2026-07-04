def test_listar_roles_admin(client, admin_headers):
    r = client.get("/api/v1/roles", headers=admin_headers)
    assert r.status_code == 200
    nombres = [x["nombre_rol"] for x in r.json()]
    assert "Administrador" in nombres


def test_listar_roles_sin_token_401(client):
    assert client.get("/api/v1/roles").status_code == 401
