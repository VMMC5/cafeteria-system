def _mesa(client, admin_headers, numero=201):
    return client.post(
        "/api/v1/mesas",
        headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()


def _producto(client, db, admin_headers, precio=50.0, disponible=True):
    from app.models import Categoria

    cat = db.query(Categoria).first()
    return client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": "Item",
            "precio_venta": precio,
            "disponible": disponible,
        },
    ).json()


def test_crear_pedido_ok(client, db, admin_headers):
    mesa = _mesa(client, admin_headers)
    prod = _producto(client, db, admin_headers, precio=50.0)
    r = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "observaciones": "Rápido",
            "items": [
                {"id_producto": prod["id_producto"], "cantidad": 2, "observaciones": None}
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["total"]) == 100.0
    assert body["estado"]["nombre_estado"] == "Pendiente"
    m = client.get(f"/api/v1/mesas/{mesa['id_mesa']}", headers=admin_headers).json()
    assert m["estado"] == "Ocupada"


def test_precio_congelado(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=202)
    prod = _producto(client, db, admin_headers, precio=50.0)
    pedido = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()
    assert float(pedido["detalle"][0]["precio_unitario"]) == 50.0


def test_mesa_ocupada_409(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=203)
    prod = _producto(client, db, admin_headers)
    payload = {
        "id_mesa": mesa["id_mesa"],
        "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
    }
    assert client.post("/api/v1/pedidos", headers=admin_headers, json=payload).status_code == 201
    assert client.post("/api/v1/pedidos", headers=admin_headers, json=payload).status_code == 409


def test_producto_no_disponible_422(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=204)
    prod = _producto(client, db, admin_headers, disponible=False)
    r = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    )
    assert r.status_code == 422


def test_sin_items_422(client, admin_headers):
    mesa = _mesa(client, admin_headers, numero=205)
    r = client.post(
        "/api/v1/pedidos", headers=admin_headers, json={"id_mesa": mesa["id_mesa"], "items": []}
    )
    assert r.status_code == 422


def test_sin_token_401(client):
    assert client.post("/api/v1/pedidos", json={"id_mesa": 1, "items": []}).status_code == 401
