from datetime import date, datetime, timezone
from decimal import Decimal


def _cobrar(client, db, admin_headers, cajero_headers, numero, precio=116.0):
    """Crea mesa+producto+pedido y lo cobra. Devuelve el dict de la venta."""
    from app.models import Categoria, MetodoPago

    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()
    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos", headers=admin_headers,
        json={"id_categoria": cat.id_categoria, "nombre_producto": f"Item{numero}",
              "precio_venta": precio, "disponible": True},
    ).json()
    pedido = client.post(
        "/api/v1/pedidos", headers=admin_headers,
        json={"id_mesa": mesa["id_mesa"],
              "items": [{"id_producto": prod["id_producto"], "cantidad": 2}]},
    ).json()
    efectivo = (
        db.query(MetodoPago).filter(MetodoPago.nombre_metodo == "Efectivo").one()
    ).id_metodo_pago
    venta = client.post(
        "/api/v1/ventas", headers=cajero_headers,
        json={"id_pedido": pedido["id_pedido"],
              "pagos": [{"id_metodo_pago": efectivo, "monto": float(precio) * 2 + 100}]},
    ).json()
    return venta


def _fechar_venta(db, id_venta, cuando: datetime):
    """Reescribe fecha_venta para probar el filtro de rango."""
    from app.models import Venta

    db.query(Venta).filter(Venta.id_venta == id_venta).update(
        {Venta.fecha_venta: cuando}
    )
    db.flush()


def test_resumen_sin_datos_ceros(client, db, admin_headers):
    r = client.get("/api/v1/reportes/resumen", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["num_ventas"] == 0
    assert float(body["total_vendido"]) == 0.0
    assert float(body["ticket_promedio"]) == 0.0
    assert float(body["utilidad_estimada"]) == 0.0


def test_resumen_agrega_ventas_de_hoy(client, db, admin_headers, cajero_headers):
    _cobrar(client, db, admin_headers, cajero_headers, numero=701, precio=100.0)
    _cobrar(client, db, admin_headers, cajero_headers, numero=702, precio=100.0)
    r = client.get("/api/v1/reportes/resumen", headers=admin_headers)
    body = r.json()
    # cada venta: 2 x 100 = 200
    assert body["num_ventas"] == 2
    assert float(body["total_vendido"]) == 400.0
    assert float(body["ticket_promedio"]) == 200.0


def test_resumen_excluye_fuera_de_rango(client, db, admin_headers, cajero_headers):
    v = _cobrar(client, db, admin_headers, cajero_headers, numero=703, precio=50.0)
    _fechar_venta(db, v["id_venta"], datetime(2020, 1, 1, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/resumen?desde=2026-07-01&hasta=2026-07-31",
        headers=admin_headers,
    )
    assert r.json()["num_ventas"] == 0


def test_resumen_requiere_admin_403(client, db, mesero_headers):
    assert client.get(
        "/api/v1/reportes/resumen", headers=mesero_headers
    ).status_code == 403


def test_resumen_sin_token_401(client):
    assert client.get("/api/v1/reportes/resumen").status_code == 401


def test_ventas_por_dia_agrupa_por_fecha(
    client, db, admin_headers, cajero_headers
):
    from datetime import datetime, timezone

    v1 = _cobrar(client, db, admin_headers, cajero_headers, numero=710, precio=100.0)
    v2 = _cobrar(client, db, admin_headers, cajero_headers, numero=711, precio=100.0)
    _fechar_venta(db, v1["id_venta"], datetime(2026, 7, 3, 12, 0, tzinfo=timezone.utc))
    _fechar_venta(db, v2["id_venta"], datetime(2026, 7, 4, 12, 0, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/ventas-por-dia?desde=2026-07-01&hasta=2026-07-31",
        headers=admin_headers,
    )
    assert r.status_code == 200
    serie = r.json()
    assert [p["fecha"] for p in serie] == ["2026-07-03", "2026-07-04"]
    assert all(p["num_ventas"] == 1 for p in serie)
    assert float(serie[0]["total"]) == 200.0


def test_ventas_por_dia_requiere_admin_403(client, db, mesero_headers):
    assert client.get(
        "/api/v1/reportes/ventas-por-dia", headers=mesero_headers
    ).status_code == 403


def test_top_productos_ordena_por_cantidad(
    client, db, admin_headers, cajero_headers
):
    # _cobrar crea un producto distinto por número y vende cantidad=2 de cada uno.
    _cobrar(client, db, admin_headers, cajero_headers, numero=720, precio=30.0)
    _cobrar(client, db, admin_headers, cajero_headers, numero=721, precio=50.0)
    r = client.get("/api/v1/reportes/top-productos?limite=5", headers=admin_headers)
    assert r.status_code == 200
    top = r.json()
    assert len(top) == 2
    # cada producto: cantidad 2, importe = 2 * precio
    importes = {p["nombre"]: float(p["importe"]) for p in top}
    assert importes["Item720"] == 60.0
    assert importes["Item721"] == 100.0
    assert all(p["cantidad"] == 2 for p in top)


def test_top_productos_respeta_limite(
    client, db, admin_headers, cajero_headers
):
    for n in range(730, 733):
        _cobrar(client, db, admin_headers, cajero_headers, numero=n, precio=20.0)
    r = client.get("/api/v1/reportes/top-productos?limite=2", headers=admin_headers)
    assert len(r.json()) == 2


def test_top_productos_requiere_admin_403(client, db, mesero_headers):
    assert client.get(
        "/api/v1/reportes/top-productos", headers=mesero_headers
    ).status_code == 403
