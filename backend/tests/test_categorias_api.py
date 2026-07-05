def _nueva():
    return {"nombre_categoria": "Snacks", "descripcion": "Botanas"}


def test_listar_requiere_auth(client):
    assert client.get("/api/v1/categorias").status_code == 401


def test_listar_autenticado(client, mesero_headers):
    r = client.get("/api/v1/categorias", headers=mesero_headers)
    assert r.status_code == 200
    assert any(c["nombre_categoria"] == "Bebidas" for c in r.json())


def test_crear_requiere_admin(client, mesero_headers):
    assert (
        client.post("/api/v1/categorias", headers=mesero_headers, json=_nueva()).status_code
        == 403
    )


def test_crear_y_duplicado(client, admin_headers):
    r = client.post("/api/v1/categorias", headers=admin_headers, json=_nueva())
    assert r.status_code == 201
    assert (
        client.post("/api/v1/categorias", headers=admin_headers, json=_nueva()).status_code
        == 409
    )


def test_editar(client, admin_headers):
    creada = client.post("/api/v1/categorias", headers=admin_headers, json=_nueva()).json()
    r = client.patch(
        f"/api/v1/categorias/{creada['id_categoria']}",
        headers=admin_headers,
        json={"descripcion": "Actualizada"},
    )
    assert r.status_code == 200 and r.json()["descripcion"] == "Actualizada"


def test_borrar_vacia_204(client, admin_headers):
    creada = client.post("/api/v1/categorias", headers=admin_headers, json=_nueva()).json()
    assert (
        client.delete(
            f"/api/v1/categorias/{creada['id_categoria']}", headers=admin_headers
        ).status_code
        == 204
    )
