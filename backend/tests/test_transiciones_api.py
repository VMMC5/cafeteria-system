def _mesa(client, admin_headers, numero):
    return client.post(
        "/api/v1/mesas",
        headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()


def _producto(client, db, admin_headers, precio=50.0):
    from app.models import Categoria

    cat = db.query(Categoria).first()
    return client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": "Item",
            "precio_venta": precio,
            "disponible": True,
        },
    ).json()


def _pedido_pendiente(client, db, admin_headers, numero):
    mesa = _mesa(client, admin_headers, numero)
    prod = _producto(client, db, admin_headers)
    return client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()


def _estado_id(db, nombre):
    from app.models import EstadoPedido

    return (
        db.query(EstadoPedido)
        .filter(EstadoPedido.nombre_estado == nombre)
        .one()
        .id_estado
    )


def _patch_estado(client, headers, id_pedido, nombre_destino, db):
    return client.patch(
        f"/api/v1/pedidos/{id_pedido}/estado",
        headers=headers,
        json={"id_estado": _estado_id(db, nombre_destino)},
    )


def test_flujo_feliz_completo(
    client, db, admin_headers, cocinero_headers, mesero_headers
):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=301)
    pid = pedido["id_pedido"]

    r1 = _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    assert r1.status_code == 200
    assert r1.json()["estado"]["nombre_estado"] == "En preparación"

    r2 = _patch_estado(client, cocinero_headers, pid, "Listo", db)
    assert r2.status_code == 200
    assert r2.json()["estado"]["nombre_estado"] == "Listo"

    r3 = _patch_estado(client, mesero_headers, pid, "Entregado", db)
    assert r3.status_code == 200
    assert r3.json()["estado"]["nombre_estado"] == "Entregado"


def test_rol_equivocado_avanzar_403(client, db, admin_headers, mesero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=302)
    # mesero no puede Pendiente -> En preparación (eso es de cocina)
    r = _patch_estado(client, mesero_headers, pedido["id_pedido"], "En preparación", db)
    assert r.status_code == 403


def test_rol_equivocado_entregar_403(client, db, admin_headers, cocinero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=303)
    pid = pedido["id_pedido"]
    _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    _patch_estado(client, cocinero_headers, pid, "Listo", db)
    # cocinero no puede Listo -> Entregado (eso es del mesero)
    r = _patch_estado(client, cocinero_headers, pid, "Entregado", db)
    assert r.status_code == 403


def test_salto_de_estado_409(client, db, admin_headers, cocinero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=304)
    # Pendiente -> Listo (salta "En preparación")
    r = _patch_estado(client, cocinero_headers, pedido["id_pedido"], "Listo", db)
    assert r.status_code == 409


def test_retroceso_409(client, db, admin_headers, cocinero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=305)
    pid = pedido["id_pedido"]
    _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    _patch_estado(client, cocinero_headers, pid, "Listo", db)
    # Listo -> En preparación es un retroceso
    r = _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    assert r.status_code == 409


def test_avanzar_terminal_409(
    client, db, admin_headers, cocinero_headers, mesero_headers
):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=306)
    pid = pedido["id_pedido"]
    _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    _patch_estado(client, cocinero_headers, pid, "Listo", db)
    _patch_estado(client, mesero_headers, pid, "Entregado", db)
    # Entregado es terminal: cualquier avance -> 409
    r = _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    assert r.status_code == 409


def test_avanzar_pedido_inexistente_404(client, db, cocinero_headers):
    r = client.patch(
        "/api/v1/pedidos/999999/estado",
        headers=cocinero_headers,
        json={"id_estado": _estado_id(db, "En preparación")},
    )
    assert r.status_code == 404


def test_avanzar_sin_token_401(client, db):
    r = client.patch(
        "/api/v1/pedidos/1/estado",
        json={"id_estado": _estado_id(db, "En preparación")},
    )
    assert r.status_code == 401
