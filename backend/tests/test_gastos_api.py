def _cat_id(db, nombre="Servicios"):
    from app.models import CategoriaGasto

    return (
        db.query(CategoriaGasto)
        .filter(CategoriaGasto.nombre_categoria == nombre)
        .one()
        .id_categoria_gasto
    )


def test_categorias_gasto_lista(client, admin_headers):
    r = client.get("/api/v1/gastos/categorias", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_categorias_gasto_sin_token_401(client):
    assert client.get("/api/v1/gastos/categorias").status_code == 401


def test_crear_gasto_ok(client, db, cajero_headers):
    cat = _cat_id(db, "Servicios")
    r = client.post(
        "/api/v1/gastos",
        headers=cajero_headers,
        json={"id_categoria_gasto": cat, "concepto": "Luz", "monto": 500.0},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["concepto"] == "Luz"
    assert body["categoria"]["nombre_categoria"] == "Servicios"
    lista = client.get("/api/v1/gastos", headers=cajero_headers).json()
    assert any(g["id_gasto"] == body["id_gasto"] for g in lista)


def test_crear_gasto_rol_mesero_403(client, db, mesero_headers):
    cat = _cat_id(db)
    r = client.post(
        "/api/v1/gastos",
        headers=mesero_headers,
        json={"id_categoria_gasto": cat, "concepto": "x", "monto": 10.0},
    )
    assert r.status_code == 403


def test_crear_gasto_monto_cero_422(client, db, cajero_headers):
    cat = _cat_id(db)
    r = client.post(
        "/api/v1/gastos",
        headers=cajero_headers,
        json={"id_categoria_gasto": cat, "concepto": "x", "monto": 0},
    )
    assert r.status_code == 422


def test_crear_gasto_concepto_vacio_422(client, db, cajero_headers):
    cat = _cat_id(db)
    r = client.post(
        "/api/v1/gastos",
        headers=cajero_headers,
        json={"id_categoria_gasto": cat, "concepto": "", "monto": 10.0},
    )
    assert r.status_code == 422


def test_crear_gasto_categoria_inexistente_422(client, cajero_headers):
    r = client.post(
        "/api/v1/gastos",
        headers=cajero_headers,
        json={"id_categoria_gasto": 99999, "concepto": "x", "monto": 10.0},
    )
    assert r.status_code == 422


def test_listar_gastos_rol_mesero_403(client, mesero_headers):
    assert client.get("/api/v1/gastos", headers=mesero_headers).status_code == 403
