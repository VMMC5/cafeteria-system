from app.services import pedido_service


def _mesa(client, admin_headers, numero):
    return client.post(
        "/api/v1/mesas",
        headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()


def _pedido_en_mesa(client, db, admin_headers, numero):
    from app.models import Categoria

    mesa = _mesa(client, admin_headers, numero)
    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": f"Item{numero}",
            "precio_venta": 116.0,
            "disponible": True,
        },
    ).json()
    pedido = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()
    return mesa, pedido


def test_tiene_pedido_activo_con_pedido_abierto(client, db, admin_headers):
    mesa, _ = _pedido_en_mesa(client, db, admin_headers, 801)
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is True


def test_tiene_pedido_activo_falso_sin_pedidos(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, 802)
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is False


def test_tiene_pedido_activo_falso_tras_cobrar(client, db, admin_headers, cajero_headers):
    from app.models import MetodoPago

    mesa, pedido = _pedido_en_mesa(client, db, admin_headers, 803)
    efectivo = (
        db.query(MetodoPago)
        .filter(MetodoPago.nombre_metodo == "Efectivo")
        .one()
        .id_metodo_pago
    )
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
        },
    )
    assert r.status_code == 201
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is False


def test_tiene_pedido_activo_falso_tras_cancelar(client, db, admin_headers):
    mesa, pedido = _pedido_en_mesa(client, db, admin_headers, 804)
    r = client.post(
        f"/api/v1/pedidos/{pedido['id_pedido']}/cancelar",
        headers=admin_headers,
        json={"motivo": "prueba"},
    )
    assert r.status_code == 200
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is False
