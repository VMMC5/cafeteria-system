def _nueva(**over):
    base = {"numero_mesa": 101, "capacidad": 4, "ubicacion": "Terraza"}
    base.update(over)
    return base


def test_listar_autenticado(client, mesero_headers):
    assert client.get("/api/v1/mesas", headers=mesero_headers).status_code == 200


def test_listar_sin_token_401(client):
    assert client.get("/api/v1/mesas").status_code == 401


def test_crear_requiere_admin(client, mesero_headers):
    assert (
        client.post("/api/v1/mesas", headers=mesero_headers, json=_nueva()).status_code
        == 403
    )


def test_crear_y_duplicado(client, admin_headers):
    assert (
        client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).status_code
        == 201
    )
    assert (
        client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).status_code
        == 409
    )


def test_estado_invalido_422(client, admin_headers):
    assert (
        client.post(
            "/api/v1/mesas", headers=admin_headers, json=_nueva(estado="Rota")
        ).status_code
        == 422
    )


def test_capacidad_invalida_422(client, admin_headers):
    assert (
        client.post(
            "/api/v1/mesas", headers=admin_headers, json=_nueva(capacidad=0)
        ).status_code
        == 422
    )


def test_crear_ocupada_a_mano_422(client, admin_headers):
    r = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(estado="Ocupada")
    )
    assert r.status_code == 422


def test_borrar_sin_pedidos_204(client, admin_headers):
    creada = client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).json()
    assert (
        client.delete(
            f"/api/v1/mesas/{creada['id_mesa']}", headers=admin_headers
        ).status_code
        == 204
    )


def test_borrar_con_pedido_409(client, db, admin, admin_headers):
    from app.models import EstadoPedido, Pedido

    creada = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=102)
    ).json()
    estado = db.query(EstadoPedido).first()
    db.add(
        Pedido(
            id_mesa=creada["id_mesa"],
            id_usuario=admin.id_usuario,
            id_estado=estado.id_estado,
        )
    )
    db.flush()
    assert (
        client.delete(
            f"/api/v1/mesas/{creada['id_mesa']}", headers=admin_headers
        ).status_code
        == 409
    )


def _mesa_con_pedido(client, db, admin_headers, numero):
    """Crea una mesa y le abre un pedido: la mesa queda Ocupada de verdad."""
    from app.models import Categoria

    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=numero)
    ).json()
    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": f"Prod{numero}",
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


def test_cambiar_estado_con_pedido_activo_409(client, db, admin_headers):
    mesa, _ = _mesa_con_pedido(client, db, admin_headers, 901)
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Disponible"},
    )
    assert r.status_code == 409


def test_marcar_ocupada_a_mano_422(client, admin_headers):
    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=902)
    ).json()
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Ocupada"},
    )
    assert r.status_code == 422


def test_disponible_a_reservada_ok(client, admin_headers):
    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=903)
    ).json()
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Reservada"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "Reservada"


def test_destrabar_mesa_ocupada_sin_pedido_activo(client, db, admin_headers):
    """Una mesa marcada Ocupada sin pedido activo (dato viejo) SÍ se puede corregir."""
    from app.models import Mesa

    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=904)
    ).json()
    obj = db.get(Mesa, mesa["id_mesa"])
    obj.estado = "Ocupada"
    db.flush()

    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Disponible"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "Disponible"


def test_reenviar_el_mismo_estado_no_falla(client, db, admin_headers):
    mesa, _ = _mesa_con_pedido(client, db, admin_headers, 905)
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Ocupada"},
    )
    assert r.status_code == 200


def test_editar_capacidad_con_pedido_activo_ok(client, db, admin_headers):
    """El guard es solo sobre `estado`: los demás campos siguen editables."""
    mesa, _ = _mesa_con_pedido(client, db, admin_headers, 906)
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"capacidad": 8},
    )
    assert r.status_code == 200
    assert r.json()["capacidad"] == 8


def test_mesa_editable_tras_cobrar(client, db, admin_headers, cajero_headers):
    from app.models import MetodoPago

    mesa, pedido = _mesa_con_pedido(client, db, admin_headers, 907)
    efectivo = (
        db.query(MetodoPago)
        .filter(MetodoPago.nombre_metodo == "Efectivo")
        .one()
        .id_metodo_pago
    )
    assert (
        client.post(
            "/api/v1/ventas",
            headers=cajero_headers,
            json={
                "ids_pedidos": [pedido["id_pedido"]],
                "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
            },
        ).status_code
        == 201
    )
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Reservada"},
    )
    assert r.status_code == 200
