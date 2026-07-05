def _cat_id(db, nombre="Bebidas"):
    from app.models import Categoria

    return db.query(Categoria).filter(Categoria.nombre_categoria == nombre).one().id_categoria


def _nuevo(db, **over):
    base = {
        "id_categoria": _cat_id(db),
        "nombre_producto": "Té Verde",
        "descripcion": "Caliente",
        "precio_venta": 35.0,
        "disponible": True,
    }
    base.update(over)
    return base


def test_crear_requiere_admin(client, db, mesero_headers):
    assert (
        client.post("/api/v1/productos", headers=mesero_headers, json=_nuevo(db)).status_code
        == 403
    )


def test_crear_devuelve_categoria_anidada(client, db, admin_headers):
    r = client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db))
    assert r.status_code == 201
    assert r.json()["categoria"]["nombre_categoria"] == "Bebidas"
    assert float(r.json()["precio_venta"]) == 35.0


def test_precio_negativo_422(client, db, admin_headers):
    assert (
        client.post(
            "/api/v1/productos", headers=admin_headers, json=_nuevo(db, precio_venta=-1)
        ).status_code
        == 422
    )


def test_categoria_inexistente_422(client, db, admin_headers):
    assert (
        client.post(
            "/api/v1/productos", headers=admin_headers, json=_nuevo(db, id_categoria=99999)
        ).status_code
        == 422
    )


def test_listar_filtra_por_categoria(client, db, admin_headers, mesero_headers):
    client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db))
    cat = _cat_id(db)
    r = client.get(f"/api/v1/productos?id_categoria={cat}", headers=mesero_headers)
    assert r.status_code == 200
    assert all(p["id_categoria"] == cat for p in r.json())


def test_soft_delete_sale_del_menu(client, db, admin_headers):
    creado = client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db)).json()
    r = client.delete(f"/api/v1/productos/{creado['id_producto']}", headers=admin_headers)
    assert r.status_code == 200 and r.json()["disponible"] is False
    menu = client.get("/api/v1/productos?disponible=true", headers=admin_headers).json()
    assert all(p["id_producto"] != creado["id_producto"] for p in menu)
