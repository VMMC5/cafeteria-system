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


def test_detalle_trae_lineas_y_total(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=210)
    prod = _producto(client, db, admin_headers, precio=20.0)
    creado = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 3}],
        },
    ).json()
    r = client.get(f"/api/v1/pedidos/{creado['id_pedido']}", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert float(body["total"]) == 60.0
    assert body["detalle"][0]["producto"]["nombre_producto"] == "Item"


def test_listar_mias(client, db, admin, admin_headers, mesero, mesero_headers):
    mesa = _mesa(client, admin_headers, numero=211)
    prod = _producto(client, db, admin_headers)
    admin_pedido = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()
    mias_del_mesero = client.get("/api/v1/pedidos?mias=true", headers=mesero_headers).json()
    assert all(p["id_pedido"] != admin_pedido["id_pedido"] for p in mias_del_mesero)
    mias_del_admin = client.get("/api/v1/pedidos?mias=true", headers=admin_headers).json()
    assert any(p["id_pedido"] == admin_pedido["id_pedido"] for p in mias_del_admin)


def test_precio_persiste_tras_cambiar_producto(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=212)
    prod = _producto(client, db, admin_headers, precio=50.0)
    creado = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()
    client.patch(
        f"/api/v1/productos/{prod['id_producto']}",
        headers=admin_headers,
        json={"precio_venta": 99.0},
    )
    r = client.get(f"/api/v1/pedidos/{creado['id_pedido']}", headers=admin_headers).json()
    assert float(r["detalle"][0]["precio_unitario"]) == 50.0


def test_detalle_inexistente_404(client, admin_headers):
    assert client.get("/api/v1/pedidos/999999", headers=admin_headers).status_code == 404
