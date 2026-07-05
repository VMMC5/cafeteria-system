def _unidad_id(db, nombre="Kilogramo"):
    from app.models import UnidadMedida

    return (
        db.query(UnidadMedida)
        .filter(UnidadMedida.nombre_unidad == nombre)
        .one()
        .id_unidad
    )


def _crear_insumo(client, db, cocinero_headers, nombre="Café en grano", stock=10.0, minimo=5.0):
    u = _unidad_id(db, "Kilogramo")
    return client.post(
        "/api/v1/insumos",
        headers=cocinero_headers,
        json={
            "nombre_insumo": nombre,
            "id_unidad": u,
            "stock_actual": stock,
            "stock_minimo": minimo,
            "costo_unitario": 200.0,
        },
    )


def test_unidades_lista(client, admin_headers):
    r = client.get("/api/v1/unidades", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 5


def test_unidades_sin_token_401(client):
    assert client.get("/api/v1/unidades").status_code == 401


def test_crear_insumo_ok(client, db, cocinero_headers):
    r = _crear_insumo(client, db, cocinero_headers)
    assert r.status_code == 201
    body = r.json()
    assert body["unidad"]["abreviatura"] == "kg"
    assert float(body["stock_actual"]) == 10.0


def test_crear_insumo_unidad_inexistente_422(client, cocinero_headers):
    r = client.post(
        "/api/v1/insumos",
        headers=cocinero_headers,
        json={"nombre_insumo": "X", "id_unidad": 99999},
    )
    assert r.status_code == 422


def test_crear_insumo_rol_mesero_403(client, db, mesero_headers):
    u = _unidad_id(db)
    r = client.post(
        "/api/v1/insumos",
        headers=mesero_headers,
        json={"nombre_insumo": "X", "id_unidad": u},
    )
    assert r.status_code == 403


def test_insumos_lista_rol(client, db, cocinero_headers, mesero_headers):
    _crear_insumo(client, db, cocinero_headers, nombre="Leche")
    assert client.get("/api/v1/insumos", headers=cocinero_headers).status_code == 200
    assert client.get("/api/v1/insumos", headers=mesero_headers).status_code == 403


def test_editar_insumo(client, db, cocinero_headers):
    insumo = _crear_insumo(client, db, cocinero_headers, nombre="Azúcar").json()
    r = client.patch(
        f"/api/v1/insumos/{insumo['id_insumo']}",
        headers=cocinero_headers,
        json={"stock_minimo": 8.0},
    )
    assert r.status_code == 200
    assert float(r.json()["stock_minimo"]) == 8.0


def test_detalle_insumo_404(client, cocinero_headers):
    assert client.get("/api/v1/insumos/999999", headers=cocinero_headers).status_code == 404
