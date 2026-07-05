def _pedido(client, db, admin_headers, numero, precio=116.0):
    from app.models import Categoria

    mesa = client.post(
        "/api/v1/mesas",
        headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()
    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": "Item",
            "precio_venta": precio,
            "disponible": True,
        },
    ).json()
    return client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()


def _metodo_id(db, nombre):
    from app.models import MetodoPago

    return (
        db.query(MetodoPago)
        .filter(MetodoPago.nombre_metodo == nombre)
        .one()
        .id_metodo_pago
    )


def test_cobrar_ok(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=601, precio=116.0)
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["total"]) == 116.0
    assert float(body["subtotal"]) == 100.0
    assert float(body["iva"]) == 16.0
    assert float(body["cambio"]) == 84.0
    assert body["folio"].startswith("V-")
    m = client.get(
        f"/api/v1/mesas/{pedido['id_mesa']}", headers=admin_headers
    ).json()
    assert m["estado"] == "Disponible"


def test_cobrar_pago_dividido_exacto(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=602, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    ta = _metodo_id(db, "Tarjeta")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [
                {"id_metodo_pago": ef, "monto": 100.0},
                {"id_metodo_pago": ta, "monto": 16.0},
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["cambio"]) == 0.0
    assert len(body["pagos"]) == 2


def test_cobrar_pago_insuficiente_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=603, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [{"id_metodo_pago": ef, "monto": 50.0}],
        },
    )
    assert r.status_code == 422


def test_cobrar_metodo_inexistente_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=604, precio=116.0)
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [{"id_metodo_pago": 99999, "monto": 200.0}],
        },
    )
    assert r.status_code == 422


def test_cobrar_pagos_vacios_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=605)
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={"id_pedido": pedido["id_pedido"], "pagos": []},
    )
    assert r.status_code == 422


def test_cobrar_pedido_cancelado_409(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=606)
    client.post(
        f"/api/v1/pedidos/{pedido['id_pedido']}/cancelar",
        headers=admin_headers,
        json={"motivo": "prueba"},
    )
    ef = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [{"id_metodo_pago": ef, "monto": 200.0}],
        },
    )
    assert r.status_code == 409


def test_cobrar_dos_veces_409(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=607, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    payload = {
        "id_pedido": pedido["id_pedido"],
        "pagos": [{"id_metodo_pago": ef, "monto": 200.0}],
    }
    assert (
        client.post("/api/v1/ventas", headers=cajero_headers, json=payload).status_code
        == 201
    )
    assert (
        client.post("/api/v1/ventas", headers=cajero_headers, json=payload).status_code
        == 409
    )


def test_cobrar_rol_mesero_403(client, db, admin_headers, mesero_headers):
    pedido = _pedido(client, db, admin_headers, numero=608, precio=116.0)
    r = client.post(
        "/api/v1/ventas",
        headers=mesero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [{"id_metodo_pago": 1, "monto": 200.0}],
        },
    )
    assert r.status_code == 403


def test_get_venta_detalle_y_404(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=609, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    venta = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [{"id_metodo_pago": ef, "monto": 116.0}],
        },
    ).json()
    r = client.get(f"/api/v1/ventas/{venta['id_venta']}", headers=cajero_headers)
    assert r.status_code == 200
    assert float(r.json()["iva"]) == 16.0
    assert len(r.json()["pagos"]) == 1
    assert client.get("/api/v1/ventas/999999", headers=cajero_headers).status_code == 404


def test_pedidos_por_cobrar(client, db, admin_headers, cajero_headers):
    p_activo = _pedido(client, db, admin_headers, numero=610)

    p_cobrado = _pedido(client, db, admin_headers, numero=611, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": p_cobrado["id_pedido"],
            "pagos": [{"id_metodo_pago": ef, "monto": 200.0}],
        },
    )

    p_cancel = _pedido(client, db, admin_headers, numero=612)
    client.post(
        f"/api/v1/pedidos/{p_cancel['id_pedido']}/cancelar",
        headers=admin_headers,
        json={"motivo": "prueba"},
    )

    r = client.get("/api/v1/pedidos?por_cobrar=true", headers=cajero_headers)
    assert r.status_code == 200
    ids = {p["id_pedido"] for p in r.json()}
    assert p_activo["id_pedido"] in ids
    assert p_cobrado["id_pedido"] not in ids
    assert p_cancel["id_pedido"] not in ids
