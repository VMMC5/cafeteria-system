def test_proveedores_lista_rol(client, cocinero_headers, mesero_headers):
    assert client.get("/api/v1/proveedores", headers=cocinero_headers).status_code == 200
    assert client.get("/api/v1/proveedores", headers=mesero_headers).status_code == 403


def test_proveedores_sin_token_401(client):
    assert client.get("/api/v1/proveedores").status_code == 401


def test_crear_proveedor_ok(client, cocinero_headers):
    r = client.post(
        "/api/v1/proveedores",
        headers=cocinero_headers,
        json={"nombre_proveedor": "Café del Norte", "telefono": "555"},
    )
    assert r.status_code == 201
    assert r.json()["nombre_proveedor"] == "Café del Norte"


def test_crear_proveedor_rol_mesero_403(client, mesero_headers):
    r = client.post(
        "/api/v1/proveedores",
        headers=mesero_headers,
        json={"nombre_proveedor": "X"},
    )
    assert r.status_code == 403
