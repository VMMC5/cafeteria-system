from datetime import date, datetime, timezone
from decimal import Decimal


def _cobrar(
    client, db, admin_headers, cajero_headers, numero, precio=116.0,
    pedido_headers=None, pagos=None,
):
    """Crea mesa+producto+pedido y lo cobra. Devuelve el dict de la venta.

    `pedido_headers` permite crear el pedido con otro usuario autenticado
    (el "mesero" queda registrado como `Pedido.id_usuario`); por defecto usa
    `admin_headers` (comportamiento histórico, sin cambios).
    `pagos` permite pasar una lista explícita de pagos (p.ej. para probar
    métodos de pago distintos o pagos divididos); por defecto un único pago
    en Efectivo que cubre el total (comportamiento histórico, sin cambios).
    """
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
        "/api/v1/pedidos", headers=pedido_headers or admin_headers,
        json={"id_mesa": mesa["id_mesa"],
              "items": [{"id_producto": prod["id_producto"], "cantidad": 2}]},
    ).json()
    if pagos is None:
        efectivo = (
            db.query(MetodoPago).filter(MetodoPago.nombre_metodo == "Efectivo").one()
        ).id_metodo_pago
        pagos = [{"id_metodo_pago": efectivo, "monto": float(precio) * 2 + 100}]
    venta = client.post(
        "/api/v1/ventas", headers=cajero_headers,
        json={"id_pedido": pedido["id_pedido"], "pagos": pagos},
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


def test_resumen_incluye_gastos_compras_y_utilidad(
    client, db, admin_headers, cajero_headers, admin
):
    from app.models import CategoriaGasto, Compra, Gasto, Proveedor

    _cobrar(client, db, admin_headers, cajero_headers, numero=704, precio=100.0)

    cat = db.query(CategoriaGasto).first()
    db.add(
        Gasto(
            id_usuario=admin.id_usuario,
            id_categoria_gasto=cat.id_categoria_gasto,
            concepto="Luz",
            monto=Decimal("50.00"),
        )
    )
    prov = Proveedor(nombre_proveedor="Prov Test")
    db.add(prov)
    db.flush()
    db.add(
        Compra(
            id_proveedor=prov.id_proveedor,
            id_usuario=admin.id_usuario,
            total=Decimal("30.00"),
        )
    )
    db.flush()

    r = client.get("/api/v1/reportes/resumen", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert float(body["total_vendido"]) == 200.0
    assert float(body["total_gastos"]) == 50.0
    assert float(body["total_compras"]) == 30.0
    assert float(body["utilidad_estimada"]) == 120.0


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


def test_ventas_por_dia_sin_token_401(client):
    assert client.get("/api/v1/reportes/ventas-por-dia").status_code == 401


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


def test_top_productos_limite_invalido_422(client, db, admin_headers):
    assert client.get(
        "/api/v1/reportes/top-productos?limite=0", headers=admin_headers
    ).status_code == 422
    assert client.get(
        "/api/v1/reportes/top-productos?limite=-1", headers=admin_headers
    ).status_code == 422


def test_top_productos_sin_token_401(client):
    assert client.get("/api/v1/reportes/top-productos").status_code == 401


def _gasto(db, admin, monto, concepto="Luz", categoria=None):
    from app.models import CategoriaGasto, Gasto

    cat = categoria or db.query(CategoriaGasto).first()
    g = Gasto(
        id_usuario=admin.id_usuario,
        id_categoria_gasto=cat.id_categoria_gasto,
        concepto=concepto,
        monto=Decimal(str(monto)),
    )
    db.add(g)
    db.flush()
    return g


def test_detalle_ventas_incluye_la_venta(client, db, admin_headers, cajero_headers):
    venta = _cobrar(client, db, admin_headers, cajero_headers, numero=801, precio=116.0)
    r = client.get("/api/v1/reportes/ventas", headers=admin_headers)
    assert r.status_code == 200
    fila = next(f for f in r.json() if f["folio"] == venta["folio"])
    assert fila["mesa"] == 801
    assert float(fila["total"]) == 232.0  # 2 x 116
    assert "Efectivo" in fila["metodos"]


def test_detalle_ventas_requiere_admin_403(client, db, mesero_headers):
    assert client.get("/api/v1/reportes/ventas", headers=mesero_headers).status_code == 403


def test_detalle_ventas_sin_token_401(client):
    assert client.get("/api/v1/reportes/ventas").status_code == 401


def test_detalle_gastos_incluye_el_gasto(client, db, admin, admin_headers):
    _gasto(db, admin, 250.0, concepto="LuzReporteTest")
    r = client.get("/api/v1/reportes/gastos", headers=admin_headers)
    assert r.status_code == 200
    fila = next(f for f in r.json() if f["concepto"] == "LuzReporteTest")
    assert float(fila["monto"]) == 250.0
    assert fila["categoria"]


def test_detalle_gastos_requiere_admin_403(client, db, mesero_headers):
    assert client.get("/api/v1/reportes/gastos", headers=mesero_headers).status_code == 403


def _fechar_gasto(db, id_gasto, cuando: datetime):
    """Reescribe fecha_gasto para probar el filtro de rango."""
    from app.models import Gasto

    db.query(Gasto).filter(Gasto.id_gasto == id_gasto).update(
        {Gasto.fecha_gasto: cuando}
    )
    db.flush()


def test_gastos_por_dia_agrupa_por_fecha(client, db, admin, admin_headers):
    # Rango en el pasado lejano (2025-03), fuera de la ventana de seed_demo
    # (últimos 60 días), para no mezclar datos ficticios con los del test.
    g1 = _gasto(db, admin, 100.0, concepto="GastoDia1A")
    g2 = _gasto(db, admin, 50.0, concepto="GastoDia1B")
    g3 = _gasto(db, admin, 30.0, concepto="GastoDia2")
    _fechar_gasto(db, g1.id_gasto, datetime(2025, 3, 3, 9, 0, tzinfo=timezone.utc))
    _fechar_gasto(db, g2.id_gasto, datetime(2025, 3, 3, 15, 0, tzinfo=timezone.utc))
    _fechar_gasto(db, g3.id_gasto, datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/gastos-por-dia?desde=2025-03-01&hasta=2025-03-31",
        headers=admin_headers,
    )
    assert r.status_code == 200
    serie = r.json()
    assert [p["fecha"] for p in serie] == ["2025-03-03", "2025-03-04"]
    assert serie[0]["num_gastos"] == 2
    assert float(serie[0]["total"]) == 150.0
    assert serie[1]["num_gastos"] == 1
    assert float(serie[1]["total"]) == 30.0


def test_gastos_por_dia_respeta_rango(client, db, admin, admin_headers):
    g = _gasto(db, admin, 999.0, concepto="GastoFueraDeRango")
    _fechar_gasto(db, g.id_gasto, datetime(2020, 1, 1, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/gastos-por-dia?desde=2025-03-01&hasta=2025-03-31",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json() == []


def test_gastos_por_dia_vacio(client, db, admin_headers):
    r = client.get(
        "/api/v1/reportes/gastos-por-dia?desde=2025-03-01&hasta=2025-03-31",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json() == []


def test_gastos_por_dia_requiere_admin_403(client, db, mesero_headers):
    assert client.get(
        "/api/v1/reportes/gastos-por-dia", headers=mesero_headers
    ).status_code == 403


def test_gastos_por_dia_sin_token_401(client):
    assert client.get("/api/v1/reportes/gastos-por-dia").status_code == 401


def test_comparativo_calcula_delta(client, db, admin_headers, cajero_headers):
    v_act = _cobrar(client, db, admin_headers, cajero_headers, numero=903, precio=100.0)  # total 200
    v_ant = _cobrar(client, db, admin_headers, cajero_headers, numero=904, precio=50.0)   # total 100
    _fechar_venta(db, v_act["id_venta"], datetime(2025, 3, 20, 12, 0, tzinfo=timezone.utc))
    _fechar_venta(db, v_ant["id_venta"], datetime(2025, 3, 19, 12, 0, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/comparativo?desde=2025-03-20&hasta=2025-03-20",
        headers=admin_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert float(body["actual"]["total_vendido"]) == 200.0
    assert float(body["anterior"]["total_vendido"]) == 100.0
    assert body["deltas"]["total_vendido"] == 100.0  # (200-100)/100*100


def test_comparativo_delta_null_sin_periodo_anterior(client, db, admin_headers, cajero_headers):
    v = _cobrar(client, db, admin_headers, cajero_headers, numero=905, precio=100.0)
    _fechar_venta(db, v["id_venta"], datetime(2025, 3, 25, 12, 0, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/comparativo?desde=2025-03-25&hasta=2025-03-25",
        headers=admin_headers,
    )
    assert r.json()["deltas"]["total_vendido"] is None


def test_comparativo_requiere_admin_403(client, db, mesero_headers):
    assert client.get("/api/v1/reportes/comparativo", headers=mesero_headers).status_code == 403


def _insumo(db, nombre, stock, minimo):
    from app.models import Insumo, UnidadMedida

    u = db.query(UnidadMedida).first()
    i = Insumo(
        id_unidad=u.id_unidad,
        nombre_insumo=nombre,
        stock_actual=Decimal(str(stock)),
        stock_minimo=Decimal(str(minimo)),
    )
    db.add(i)
    db.flush()
    return i


def test_inventario_niveles_pct_y_bajo_minimo(client, db, admin_headers):
    _insumo(db, "InsumoBajoXYZ", 1, 10)    # bajo mínimo; 1/(2*10)*100 = 5
    _insumo(db, "InsumoOkXYZ", 100, 10)    # 100/(2*10)*100 = 500 -> tope 100
    filas = {f["nombre"]: f for f in client.get(
        "/api/v1/reportes/inventario-niveles", headers=admin_headers).json()}
    assert filas["InsumoBajoXYZ"]["nivel_pct"] == 5
    assert filas["InsumoBajoXYZ"]["bajo_minimo"] is True
    assert filas["InsumoOkXYZ"]["nivel_pct"] == 100
    assert filas["InsumoOkXYZ"]["bajo_minimo"] is False


def test_inventario_niveles_minimo_cero(client, db, admin_headers):
    _insumo(db, "InsumoCeroMinXYZ", 5, 0)
    filas = {f["nombre"]: f for f in client.get(
        "/api/v1/reportes/inventario-niveles", headers=admin_headers).json()}
    assert filas["InsumoCeroMinXYZ"]["nivel_pct"] == 100
    assert filas["InsumoCeroMinXYZ"]["bajo_minimo"] is False


def test_inventario_niveles_requiere_admin_403(client, db, mesero_headers):
    assert client.get(
        "/api/v1/reportes/inventario-niveles", headers=mesero_headers).status_code == 403


# --- Filtros opcionales en /reportes/ventas -------------------------------


def test_detalle_ventas_sin_filtro_incluye_ambos_meseros(
    client, db, admin_headers, cajero_headers
):
    """No-regresión: sin id_usuario, el resultado no cambia (siguen ambas)."""
    from tests.conftest import _crear_usuario, _headers

    _crear_usuario(db, "meserosinfxyz", "mesero.sinf.xyz@cafeteria.com", "Mesero")
    _crear_usuario(db, "meserosinfxyz2", "mesero.sinf2.xyz@cafeteria.com", "Mesero")
    headers_a = _headers(client, "mesero.sinf.xyz@cafeteria.com")
    headers_b = _headers(client, "mesero.sinf2.xyz@cafeteria.com")
    v_a = _cobrar(
        client, db, admin_headers, cajero_headers, numero=850, precio=50.0,
        pedido_headers=headers_a,
    )
    v_b = _cobrar(
        client, db, admin_headers, cajero_headers, numero=851, precio=60.0,
        pedido_headers=headers_b,
    )
    r = client.get("/api/v1/reportes/ventas", headers=admin_headers)
    assert r.status_code == 200
    folios = {f["folio"] for f in r.json()}
    assert {v_a["folio"], v_b["folio"]} <= folios


def test_detalle_ventas_filtra_por_mesero(client, db, admin_headers, cajero_headers):
    from tests.conftest import _crear_usuario, _headers

    mesero_a = _crear_usuario(db, "meserofxyz", "mesero.f.xyz@cafeteria.com", "Mesero")
    _crear_usuario(db, "meserofxyz2", "mesero.f2.xyz@cafeteria.com", "Mesero")
    headers_a = _headers(client, "mesero.f.xyz@cafeteria.com")
    headers_b = _headers(client, "mesero.f2.xyz@cafeteria.com")
    v_a = _cobrar(
        client, db, admin_headers, cajero_headers, numero=852, precio=50.0,
        pedido_headers=headers_a,
    )
    v_b = _cobrar(
        client, db, admin_headers, cajero_headers, numero=853, precio=60.0,
        pedido_headers=headers_b,
    )
    r = client.get(
        f"/api/v1/reportes/ventas?id_usuario={mesero_a.id_usuario}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    folios = {f["folio"] for f in r.json()}
    assert v_a["folio"] in folios
    assert v_b["folio"] not in folios


def test_detalle_ventas_sin_filtro_incluye_todos_los_metodos(
    client, db, admin_headers, cajero_headers
):
    from app.models import MetodoPago

    tarjeta_id = (
        db.query(MetodoPago).filter(MetodoPago.nombre_metodo == "Tarjeta").one()
    ).id_metodo_pago
    v_efectivo = _cobrar(client, db, admin_headers, cajero_headers, numero=860, precio=40.0)
    v_tarjeta = _cobrar(
        client, db, admin_headers, cajero_headers, numero=861, precio=40.0,
        pagos=[{"id_metodo_pago": tarjeta_id, "monto": 80.0}],
    )
    r = client.get("/api/v1/reportes/ventas", headers=admin_headers)
    assert r.status_code == 200
    folios = {f["folio"] for f in r.json()}
    assert {v_efectivo["folio"], v_tarjeta["folio"]} <= folios


def test_detalle_ventas_filtra_por_metodo_incluye_pago_dividido(
    client, db, admin_headers, cajero_headers
):
    from app.models import MetodoPago

    tarjeta_id = (
        db.query(MetodoPago).filter(MetodoPago.nombre_metodo == "Tarjeta").one()
    ).id_metodo_pago
    efectivo_id = (
        db.query(MetodoPago).filter(MetodoPago.nombre_metodo == "Efectivo").one()
    ).id_metodo_pago

    v_efectivo = _cobrar(client, db, admin_headers, cajero_headers, numero=862, precio=40.0)
    v_tarjeta = _cobrar(
        client, db, admin_headers, cajero_headers, numero=863, precio=40.0,
        pagos=[{"id_metodo_pago": tarjeta_id, "monto": 80.0}],
    )
    v_dividida = _cobrar(
        client, db, admin_headers, cajero_headers, numero=864, precio=40.0,
        pagos=[
            {"id_metodo_pago": efectivo_id, "monto": 30.0},
            {"id_metodo_pago": tarjeta_id, "monto": 50.0},
        ],
    )

    r = client.get(
        f"/api/v1/reportes/ventas?id_metodo={tarjeta_id}", headers=admin_headers
    )
    assert r.status_code == 200
    folios = [f["folio"] for f in r.json()]
    assert v_tarjeta["folio"] in folios
    assert v_dividida["folio"] in folios
    assert v_efectivo["folio"] not in folios
    # la venta con pago dividido aparece una sola vez (sin duplicar filas)
    assert folios.count(v_dividida["folio"]) == 1


# --- Filtros opcionales en /reportes/gastos --------------------------------


def test_detalle_gastos_sin_filtro_incluye_todo(client, db, admin, cajero, admin_headers):
    g_admin = _gasto(db, admin, 50.0, concepto="GastoSinFAdminXYZ")
    g_cajero = _gasto(db, cajero, 60.0, concepto="GastoSinFCajeroXYZ")
    r = client.get("/api/v1/reportes/gastos", headers=admin_headers)
    assert r.status_code == 200
    conceptos = {f["concepto"] for f in r.json()}
    assert {"GastoSinFAdminXYZ", "GastoSinFCajeroXYZ"} <= conceptos
    assert g_admin.id_gasto and g_cajero.id_gasto  # sanidad: se crearon


def test_detalle_gastos_filtra_por_usuario(client, db, admin, cajero, admin_headers):
    _gasto(db, admin, 50.0, concepto="GastoFUAdminXYZ")
    _gasto(db, cajero, 60.0, concepto="GastoFUCajeroXYZ")
    r = client.get(
        f"/api/v1/reportes/gastos?id_usuario={cajero.id_usuario}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    conceptos = {f["concepto"] for f in r.json()}
    assert "GastoFUCajeroXYZ" in conceptos
    assert "GastoFUAdminXYZ" not in conceptos


def test_detalle_gastos_filtra_por_categoria(client, db, admin, admin_headers):
    from app.models import CategoriaGasto

    servicios = (
        db.query(CategoriaGasto)
        .filter(CategoriaGasto.nombre_categoria == "Servicios")
        .one()
    )
    nomina = (
        db.query(CategoriaGasto)
        .filter(CategoriaGasto.nombre_categoria == "Nómina")
        .one()
    )
    _gasto(db, admin, 111.0, concepto="GastoFCServiciosXYZ", categoria=servicios)
    _gasto(db, admin, 222.0, concepto="GastoFCNominaXYZ", categoria=nomina)
    r = client.get(
        f"/api/v1/reportes/gastos?id_categoria={servicios.id_categoria_gasto}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    conceptos = {f["concepto"] for f in r.json()}
    assert "GastoFCServiciosXYZ" in conceptos
    assert "GastoFCNominaXYZ" not in conceptos


# --- Flag opcional en /reportes/inventario-niveles -------------------------


def test_inventario_niveles_sin_filtro_incluye_todos(client, db, admin_headers):
    _insumo(db, "InsumoBajoSinFXYZ", 1, 10)
    _insumo(db, "InsumoOkSinFXYZ", 100, 10)
    r = client.get("/api/v1/reportes/inventario-niveles", headers=admin_headers)
    assert r.status_code == 200
    nombres = {f["nombre"] for f in r.json()}
    assert {"InsumoBajoSinFXYZ", "InsumoOkSinFXYZ"} <= nombres


def test_inventario_niveles_solo_bajo_minimo_filtra(client, db, admin_headers):
    _insumo(db, "InsumoBajoFXYZ", 1, 10)
    _insumo(db, "InsumoOkFXYZ", 100, 10)
    r = client.get(
        "/api/v1/reportes/inventario-niveles?solo_bajo_minimo=true",
        headers=admin_headers,
    )
    assert r.status_code == 200
    nombres = {f["nombre"] for f in r.json()}
    assert "InsumoBajoFXYZ" in nombres
    assert "InsumoOkFXYZ" not in nombres


# --- Nuevo endpoint: /reportes/estado-resultados ---------------------------


def _compra(db, admin, total, proveedor_nombre="ProvEstadoResultadosXYZ"):
    from app.models import Compra, Proveedor

    prov = Proveedor(nombre_proveedor=proveedor_nombre)
    db.add(prov)
    db.flush()
    c = Compra(
        id_proveedor=prov.id_proveedor,
        id_usuario=admin.id_usuario,
        total=Decimal(str(total)),
    )
    db.add(c)
    db.flush()
    return c


def _fechar_compra(db, id_compra, cuando: datetime):
    from app.models import Compra

    db.query(Compra).filter(Compra.id_compra == id_compra).update(
        {Compra.fecha_compra: cuando}
    )
    db.flush()


def test_estado_resultados_agrupa_por_dia(
    client, db, admin, admin_headers, cajero_headers
):
    v1 = _cobrar(client, db, admin_headers, cajero_headers, numero=870, precio=100.0)  # 200
    v2 = _cobrar(client, db, admin_headers, cajero_headers, numero=871, precio=50.0)   # 100
    _fechar_venta(db, v1["id_venta"], datetime(2025, 3, 3, 12, 0, tzinfo=timezone.utc))
    _fechar_venta(db, v2["id_venta"], datetime(2025, 3, 4, 12, 0, tzinfo=timezone.utc))

    g1 = _gasto(db, admin, 30.0, concepto="EResDiaGastoXYZ")
    _fechar_gasto(db, g1.id_gasto, datetime(2025, 3, 3, 9, 0, tzinfo=timezone.utc))

    c1 = _compra(db, admin, 20.0)
    _fechar_compra(db, c1.id_compra, datetime(2025, 3, 4, 9, 0, tzinfo=timezone.utc))

    r = client.get(
        "/api/v1/reportes/estado-resultados"
        "?desde=2025-03-01&hasta=2025-03-31&agrupar=dia",
        headers=admin_headers,
    )
    assert r.status_code == 200
    serie = {f["periodo"]: f for f in r.json()}
    assert "2025-03-03" in serie
    assert "2025-03-04" in serie

    d3 = serie["2025-03-03"]
    assert float(d3["ventas"]) == 200.0
    assert float(d3["gastos"]) == 30.0
    assert float(d3["compras"]) == 0.0
    assert float(d3["utilidad"]) == 170.0

    d4 = serie["2025-03-04"]
    assert float(d4["ventas"]) == 100.0
    assert float(d4["gastos"]) == 0.0
    assert float(d4["compras"]) == 20.0
    assert float(d4["utilidad"]) == 80.0

    periodos = [f["periodo"] for f in r.json()]
    assert periodos == sorted(periodos)


def test_estado_resultados_agrupa_por_mes(
    client, db, admin_headers, cajero_headers
):
    v1 = _cobrar(client, db, admin_headers, cajero_headers, numero=872, precio=100.0)  # 200
    v2 = _cobrar(client, db, admin_headers, cajero_headers, numero=873, precio=100.0)  # 200
    _fechar_venta(db, v1["id_venta"], datetime(2025, 3, 3, 12, 0, tzinfo=timezone.utc))
    _fechar_venta(db, v2["id_venta"], datetime(2025, 3, 25, 12, 0, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/estado-resultados"
        "?desde=2025-03-01&hasta=2025-03-31&agrupar=mes",
        headers=admin_headers,
    )
    assert r.status_code == 200
    serie = r.json()
    assert len(serie) == 1
    assert serie[0]["periodo"] == "2025-03"
    assert float(serie[0]["ventas"]) == 400.0
    assert float(serie[0]["utilidad"]) == 400.0


def test_estado_resultados_agrupa_por_semana(
    client, db, admin_headers, cajero_headers
):
    # 2025-03-03 es lunes; semana ISO Postgres (date_trunc) va lun 03 -> dom 09.
    v1 = _cobrar(client, db, admin_headers, cajero_headers, numero=874, precio=100.0)  # 200
    v2 = _cobrar(client, db, admin_headers, cajero_headers, numero=875, precio=50.0)   # 100, misma semana
    v3 = _cobrar(client, db, admin_headers, cajero_headers, numero=876, precio=70.0)   # 140, semana siguiente
    _fechar_venta(db, v1["id_venta"], datetime(2025, 3, 3, 8, 0, tzinfo=timezone.utc))
    _fechar_venta(db, v2["id_venta"], datetime(2025, 3, 6, 8, 0, tzinfo=timezone.utc))
    _fechar_venta(db, v3["id_venta"], datetime(2025, 3, 10, 8, 0, tzinfo=timezone.utc))
    r = client.get(
        "/api/v1/reportes/estado-resultados"
        "?desde=2025-03-01&hasta=2025-03-31&agrupar=semana",
        headers=admin_headers,
    )
    assert r.status_code == 200
    serie = r.json()
    assert len(serie) == 2
    assert serie[0]["periodo"] == "2025-03-03"
    assert float(serie[0]["ventas"]) == 300.0
    assert serie[1]["periodo"] == "2025-03-10"
    assert float(serie[1]["ventas"]) == 140.0


def test_estado_resultados_mes_filtra_fecha_cruda_no_bucket(
    client, db, admin_headers, cajero_headers
):
    """Regresión: el filtro debe aplicarse sobre la fecha cruda de cada
    transacción, no sobre el bucket truncado (date_trunc). Con un rango NO
    alineado a mes completo (desde=10-mar, hasta=20-abr):
    - una venta el 2025-03-20 está DENTRO del rango pero su bucket
      (2025-03-01) cae antes de `desde` -> con el bug quedaba excluida.
    - una venta el 2025-04-25 está FUERA del rango pero su bucket
      (2025-04-01) cae antes de `hasta` -> con el bug se colaba incluida.
    """
    v_en_rango = _cobrar(
        client, db, admin_headers, cajero_headers, numero=877, precio=100.0
    )  # total 200
    v_fuera_rango = _cobrar(
        client, db, admin_headers, cajero_headers, numero=878, precio=60.0
    )  # total 120
    _fechar_venta(
        db, v_en_rango["id_venta"], datetime(2025, 3, 20, 12, 0, tzinfo=timezone.utc)
    )
    _fechar_venta(
        db, v_fuera_rango["id_venta"], datetime(2025, 4, 25, 12, 0, tzinfo=timezone.utc)
    )

    r = client.get(
        "/api/v1/reportes/estado-resultados"
        "?desde=2025-03-10&hasta=2025-04-20&agrupar=mes",
        headers=admin_headers,
    )
    assert r.status_code == 200
    serie = {f["periodo"]: f for f in r.json()}
    assert "2025-03" in serie
    assert float(serie["2025-03"]["ventas"]) == 200.0
    assert "2025-04" not in serie


def test_estado_resultados_semana_desde_mitad_de_semana_incluye_transaccion(
    client, db, admin_headers, cajero_headers
):
    """Regresión: con agrupar=semana y un `desde` que cae a mitad de semana,
    una venta posterior a `desde` cuyo bucket (inicio de semana, lunes) es
    anterior a `desde` debe seguir incluida en el reporte."""
    v = _cobrar(
        client, db, admin_headers, cajero_headers, numero=879, precio=100.0
    )  # total 200
    # 2025-03-06 es jueves; la semana (lunes) inicia 2025-03-03.
    _fechar_venta(db, v["id_venta"], datetime(2025, 3, 6, 12, 0, tzinfo=timezone.utc))

    r = client.get(
        "/api/v1/reportes/estado-resultados"
        "?desde=2025-03-05&hasta=2025-03-31&agrupar=semana",
        headers=admin_headers,
    )
    assert r.status_code == 200
    serie = {f["periodo"]: f for f in r.json()}
    assert "2025-03-03" in serie
    assert float(serie["2025-03-03"]["ventas"]) == 200.0


def test_estado_resultados_rango_vacio(client, db, admin_headers):
    r = client.get(
        "/api/v1/reportes/estado-resultados"
        "?desde=2025-03-01&hasta=2025-03-31&agrupar=dia",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json() == []


def test_estado_resultados_agrupar_invalido_422(client, db, admin_headers):
    r = client.get(
        "/api/v1/reportes/estado-resultados?agrupar=anual",
        headers=admin_headers,
    )
    assert r.status_code == 422


def test_estado_resultados_requiere_admin_403(client, db, mesero_headers):
    assert client.get(
        "/api/v1/reportes/estado-resultados", headers=mesero_headers
    ).status_code == 403


def test_estado_resultados_sin_token_401(client):
    assert client.get("/api/v1/reportes/estado-resultados").status_code == 401
