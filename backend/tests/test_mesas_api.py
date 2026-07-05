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


def test_editar_estado(client, admin_headers):
    creada = client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).json()
    r = client.patch(
        f"/api/v1/mesas/{creada['id_mesa']}", headers=admin_headers, json={"estado": "Ocupada"}
    )
    assert r.status_code == 200 and r.json()["estado"] == "Ocupada"


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
