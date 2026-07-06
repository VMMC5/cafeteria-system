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


def _proveedor_id(client, cocinero_headers, nombre="Proveedor Test"):
    return client.post(
        "/api/v1/proveedores",
        headers=cocinero_headers,
        json={"nombre_proveedor": nombre},
    ).json()["id_proveedor"]


def _insumo(client, db, cocinero_headers, nombre="Café grano", stock=10.0):
    from app.models import UnidadMedida

    u = (
        db.query(UnidadMedida)
        .filter(UnidadMedida.nombre_unidad == "Kilogramo")
        .one()
        .id_unidad
    )
    return client.post(
        "/api/v1/insumos",
        headers=cocinero_headers,
        json={
            "nombre_insumo": nombre,
            "id_unidad": u,
            "stock_actual": stock,
            "stock_minimo": 0,
            "costo_unitario": 0,
        },
    ).json()


def _stock_costo(client, cocinero_headers, id_insumo):
    j = client.get(f"/api/v1/insumos/{id_insumo}", headers=cocinero_headers).json()
    return float(j["stock_actual"]), float(j["costo_unitario"])


def test_crear_compra_ok(client, db, cocinero_headers):
    prov = _proveedor_id(client, cocinero_headers)
    ins = _insumo(client, db, cocinero_headers, nombre="Leche compra", stock=10.0)
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": prov,
            "folio_factura": "F-1",
            "items": [
                {"id_insumo": ins["id_insumo"], "cantidad": 5.0, "costo_unitario": 20.0}
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["total"]) == 100.0
    stock, costo = _stock_costo(client, cocinero_headers, ins["id_insumo"])
    assert stock == 15.0
    assert costo == 20.0
    from app.models import MovimientoInventario

    movs = (
        db.query(MovimientoInventario)
        .filter(MovimientoInventario.id_compra == body["id_compra"])
        .all()
    )
    assert len(movs) == 1
    assert movs[0].motivo == "Compra"


def test_crear_compra_multi_linea_total(client, db, cocinero_headers):
    prov = _proveedor_id(client, cocinero_headers, "Multi")
    i1 = _insumo(client, db, cocinero_headers, nombre="A")
    i2 = _insumo(client, db, cocinero_headers, nombre="B")
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": prov,
            "items": [
                {"id_insumo": i1["id_insumo"], "cantidad": 2.0, "costo_unitario": 30.0},
                {"id_insumo": i2["id_insumo"], "cantidad": 1.0, "costo_unitario": 10.0},
            ],
        },
    )
    assert r.status_code == 201
    assert float(r.json()["total"]) == 70.0
    assert len(r.json()["detalle"]) == 2


def test_crear_compra_proveedor_inexistente_422(client, db, cocinero_headers):
    ins = _insumo(client, db, cocinero_headers, nombre="C")
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": 99999,
            "items": [
                {"id_insumo": ins["id_insumo"], "cantidad": 1.0, "costo_unitario": 5.0}
            ],
        },
    )
    assert r.status_code == 422


def test_crear_compra_insumo_inexistente_422(client, cocinero_headers):
    prov = _proveedor_id(client, cocinero_headers, "ProvX")
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": prov,
            "items": [{"id_insumo": 99999, "cantidad": 1.0, "costo_unitario": 5.0}],
        },
    )
    assert r.status_code == 422


def test_crear_compra_items_vacios_422(client, cocinero_headers):
    prov = _proveedor_id(client, cocinero_headers, "ProvY")
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={"id_proveedor": prov, "items": []},
    )
    assert r.status_code == 422


def test_crear_compra_rol_mesero_403(client, db, cocinero_headers, mesero_headers):
    prov = _proveedor_id(client, cocinero_headers, "ProvZ")
    ins = _insumo(client, db, cocinero_headers, nombre="D")
    r = client.post(
        "/api/v1/compras",
        headers=mesero_headers,
        json={
            "id_proveedor": prov,
            "items": [
                {"id_insumo": ins["id_insumo"], "cantidad": 1.0, "costo_unitario": 5.0}
            ],
        },
    )
    assert r.status_code == 403


def test_listar_compras(client, db, cocinero_headers):
    prov = _proveedor_id(client, cocinero_headers, "ProvList")
    ins = _insumo(client, db, cocinero_headers, nombre="E")
    compra = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": prov,
            "items": [
                {"id_insumo": ins["id_insumo"], "cantidad": 1.0, "costo_unitario": 5.0}
            ],
        },
    ).json()
    lista = client.get("/api/v1/compras", headers=cocinero_headers).json()
    assert any(c["id_compra"] == compra["id_compra"] for c in lista)
