def _insumo_id(client, db, cocinero_headers, nombre="Café", stock=100.0):
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
            "costo_unitario": 100.0,
        },
    ).json()["id_insumo"]


def _producto_id(client, db, admin_headers, nombre="Latte"):
    from app.models import Categoria

    cat = db.query(Categoria).first()
    return client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": nombre,
            "precio_venta": 50.0,
            "disponible": True,
        },
    ).json()["id_producto"]


def test_agregar_linea_ok(client, db, admin_headers, cocinero_headers):
    pid = _producto_id(client, db, admin_headers)
    iid = _insumo_id(client, db, cocinero_headers)
    r = client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=cocinero_headers,
        json={"id_insumo": iid, "cantidad_requerida": 0.02},
    )
    assert r.status_code == 201
    assert r.json()["insumo"]["nombre_insumo"] == "Café"
    lista = client.get(
        f"/api/v1/productos/{pid}/receta", headers=cocinero_headers
    ).json()
    assert len(lista) == 1


def test_eliminar_linea(client, db, admin_headers, cocinero_headers):
    pid = _producto_id(client, db, admin_headers, nombre="Moka")
    iid = _insumo_id(client, db, cocinero_headers, nombre="Cacao")
    linea = client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=cocinero_headers,
        json={"id_insumo": iid, "cantidad_requerida": 0.01},
    ).json()
    r = client.delete(
        f"/api/v1/productos/{pid}/receta/{linea['id_producto_insumo']}",
        headers=cocinero_headers,
    )
    assert r.status_code == 204
    assert (
        client.get(f"/api/v1/productos/{pid}/receta", headers=cocinero_headers).json()
        == []
    )


def test_receta_producto_404(client, cocinero_headers):
    r = client.post(
        "/api/v1/productos/999999/receta",
        headers=cocinero_headers,
        json={"id_insumo": 1, "cantidad_requerida": 1.0},
    )
    assert r.status_code == 404


def test_receta_insumo_inexistente_422(client, db, admin_headers, cocinero_headers):
    pid = _producto_id(client, db, admin_headers, nombre="Americano")
    r = client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=cocinero_headers,
        json={"id_insumo": 99999, "cantidad_requerida": 1.0},
    )
    assert r.status_code == 422


def test_receta_cantidad_cero_422(client, db, admin_headers, cocinero_headers):
    pid = _producto_id(client, db, admin_headers, nombre="Cortado")
    iid = _insumo_id(client, db, cocinero_headers, nombre="Espresso")
    r = client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=cocinero_headers,
        json={"id_insumo": iid, "cantidad_requerida": 0},
    )
    assert r.status_code == 422


def test_receta_duplicado_409(client, db, admin_headers, cocinero_headers):
    pid = _producto_id(client, db, admin_headers, nombre="Chai")
    iid = _insumo_id(client, db, cocinero_headers, nombre="Especias")
    payload = {"id_insumo": iid, "cantidad_requerida": 0.03}
    assert (
        client.post(
            f"/api/v1/productos/{pid}/receta", headers=cocinero_headers, json=payload
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/v1/productos/{pid}/receta", headers=cocinero_headers, json=payload
        ).status_code
        == 409
    )


def test_receta_rol_mesero_403(client, db, admin_headers, mesero_headers):
    pid = _producto_id(client, db, admin_headers, nombre="Frappe")
    r = client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=mesero_headers,
        json={"id_insumo": 1, "cantidad_requerida": 1.0},
    )
    assert r.status_code == 403
