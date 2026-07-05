def _estado_id(db, nombre):
    from app.models import EstadoPedido

    return (
        db.query(EstadoPedido)
        .filter(EstadoPedido.nombre_estado == nombre)
        .one()
        .id_estado
    )


def _crear_pedido(client, db, admin_headers, numero):
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
            "precio_venta": 10.0,
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


def _avanzar(client, headers, id_pedido, db, nombre_destino):
    return client.patch(
        f"/api/v1/pedidos/{id_pedido}/estado",
        headers=headers,
        json={"id_estado": _estado_id(db, nombre_destino)},
    )


def test_estados_lista(client, admin_headers):
    r = client.get("/api/v1/estados", headers=admin_headers)
    assert r.status_code == 200
    nombres = [e["nombre_estado"] for e in r.json()]
    assert len(r.json()) == 5
    assert "Pendiente" in nombres
    assert "Entregado" in nombres


def test_estados_sin_token_401(client):
    assert client.get("/api/v1/estados").status_code == 401


def test_listar_por_estados_csv(
    client, db, admin_headers, cocinero_headers, mesero_headers
):
    p_pend = _crear_pedido(client, db, admin_headers, numero=401)
    p_prep = _crear_pedido(client, db, admin_headers, numero=402)
    p_entregado = _crear_pedido(client, db, admin_headers, numero=403)

    _avanzar(client, cocinero_headers, p_prep["id_pedido"], db, "En preparación")
    _avanzar(client, cocinero_headers, p_entregado["id_pedido"], db, "En preparación")
    _avanzar(client, cocinero_headers, p_entregado["id_pedido"], db, "Listo")
    _avanzar(client, mesero_headers, p_entregado["id_pedido"], db, "Entregado")

    pend_id = _estado_id(db, "Pendiente")
    prep_id = _estado_id(db, "En preparación")
    r = client.get(
        f"/api/v1/pedidos?estados={pend_id},{prep_id}", headers=admin_headers
    )
    assert r.status_code == 200
    ids = {p["id_pedido"] for p in r.json()}
    assert p_pend["id_pedido"] in ids
    assert p_prep["id_pedido"] in ids
    assert p_entregado["id_pedido"] not in ids


def test_listar_id_estado_compat(client, db, admin_headers):
    p = _crear_pedido(client, db, admin_headers, numero=410)
    pend_id = _estado_id(db, "Pendiente")
    r = client.get(f"/api/v1/pedidos?id_estado={pend_id}", headers=admin_headers)
    assert r.status_code == 200
    assert all(x["estado"]["nombre_estado"] == "Pendiente" for x in r.json())
    assert any(x["id_pedido"] == p["id_pedido"] for x in r.json())
