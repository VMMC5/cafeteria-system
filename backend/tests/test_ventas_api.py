import threading
import time
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.orm import Session as OrmSession

from app.models import (
    DetallePedido,
    EstadoPedido,
    Mesa,
    MetodoPago,
    Pedido,
    Producto,
    Usuario,
    Venta,
)
from app.schemas.venta import PagoIn, VentaCreate
from app.services import venta_service
from tests.conftest import engine as _engine


def _pedido(client, db, admin_headers, numero, precio=116.0):
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
            "precio_venta": precio,
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


def _metodo_id(db, nombre):
    from app.models import MetodoPago

    return (
        db.query(MetodoPago)
        .filter(MetodoPago.nombre_metodo == nombre)
        .one()
        .id_metodo_pago
    )


def test_cobrar_ok(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=601, precio=116.0)
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["total"]) == 116.0
    assert float(body["subtotal"]) == 100.0
    assert float(body["iva"]) == 16.0
    assert float(body["cambio"]) == 84.0
    assert body["folio"].startswith("V-")
    m = client.get(
        f"/api/v1/mesas/{pedido['id_mesa']}", headers=admin_headers
    ).json()
    assert m["estado"] == "Disponible"


def test_cobrar_pago_dividido_exacto(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=602, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    ta = _metodo_id(db, "Tarjeta")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [
                {"id_metodo_pago": ef, "monto": 100.0},
                {"id_metodo_pago": ta, "monto": 16.0},
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["cambio"]) == 0.0
    assert len(body["pagos"]) == 2


def test_cobrar_pago_insuficiente_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=603, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": ef, "monto": 50.0}],
        },
    )
    assert r.status_code == 422


def test_cobrar_metodo_inexistente_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=604, precio=116.0)
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": 99999, "monto": 200.0}],
        },
    )
    assert r.status_code == 422


def test_cobrar_pagos_vacios_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=605)
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={"ids_pedidos": [pedido["id_pedido"]], "pagos": []},
    )
    assert r.status_code == 422


def test_cobrar_pedido_cancelado_409(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=606)
    client.post(
        f"/api/v1/pedidos/{pedido['id_pedido']}/cancelar",
        headers=admin_headers,
        json={"motivo": "prueba"},
    )
    ef = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": ef, "monto": 200.0}],
        },
    )
    assert r.status_code == 409


def test_cobrar_dos_veces_409(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=607, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    payload = {
        "ids_pedidos": [pedido["id_pedido"]],
        "pagos": [{"id_metodo_pago": ef, "monto": 200.0}],
    }
    assert (
        client.post("/api/v1/ventas", headers=cajero_headers, json=payload).status_code
        == 201
    )
    assert (
        client.post("/api/v1/ventas", headers=cajero_headers, json=payload).status_code
        == 409
    )


def test_cobrar_rol_mesero_403(client, db, admin_headers, mesero_headers):
    pedido = _pedido(client, db, admin_headers, numero=608, precio=116.0)
    r = client.post(
        "/api/v1/ventas",
        headers=mesero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": 1, "monto": 200.0}],
        },
    )
    assert r.status_code == 403


def test_get_venta_detalle_y_404(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=609, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    venta = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": ef, "monto": 116.0}],
        },
    ).json()
    r = client.get(f"/api/v1/ventas/{venta['id_venta']}", headers=cajero_headers)
    assert r.status_code == 200
    assert float(r.json()["iva"]) == 16.0
    assert len(r.json()["pagos"]) == 1
    assert client.get("/api/v1/ventas/999999", headers=cajero_headers).status_code == 404


def test_pedidos_por_cobrar(client, db, admin_headers, cajero_headers):
    p_activo = _pedido(client, db, admin_headers, numero=610)

    p_cobrado = _pedido(client, db, admin_headers, numero=611, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [p_cobrado["id_pedido"]],
            "pagos": [{"id_metodo_pago": ef, "monto": 200.0}],
        },
    )

    p_cancel = _pedido(client, db, admin_headers, numero=612)
    client.post(
        f"/api/v1/pedidos/{p_cancel['id_pedido']}/cancelar",
        headers=admin_headers,
        json={"motivo": "prueba"},
    )

    r = client.get("/api/v1/pedidos?por_cobrar=true", headers=cajero_headers)
    assert r.status_code == 200
    ids = {p["id_pedido"] for p in r.json()}
    assert p_activo["id_pedido"] in ids
    assert p_cobrado["id_pedido"] not in ids
    assert p_cancel["id_pedido"] not in ids


def test_cobrar_pago_dividido_excedente_y_referencia(
    client, db, admin_headers, cajero_headers
):
    """El caso del smoke manual del PR #22 que nunca tuvo test: pago dividido
    donde el Efectivo trae excedente (genera cambio) y la Tarjeta lleva
    referencia. La referencia debe persistir y el cambio ser suma − total."""
    pedido = _pedido(client, db, admin_headers, numero=606, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    ta = _metodo_id(db, "Tarjeta")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [
                {"id_metodo_pago": ef, "monto": 150.0},
                {"id_metodo_pago": ta, "monto": 16.0, "referencia": "V-123"},
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["cambio"]) == 50.0  # 166 − 116
    assert len(body["pagos"]) == 2
    # Por método, no por índice: el orden de la relación no está garantizado.
    por_metodo = {p["id_metodo_pago"]: p for p in body["pagos"]}
    assert por_metodo[ta]["referencia"] == "V-123"
    assert por_metodo[ef]["referencia"] is None
    m = client.get(f"/api/v1/mesas/{pedido['id_mesa']}", headers=admin_headers).json()
    assert m["estado"] == "Disponible"


def _otra_ronda(client, db, admin_headers, id_mesa, precio=58.0):
    """Segundo pedido sobre la MISMA mesa (ronda adicional)."""
    from app.models import Categoria

    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": "Ronda 2",
            "precio_venta": precio,
            "disponible": True,
        },
    ).json()
    r = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": id_mesa,
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    )
    assert r.status_code == 201
    return r.json()


def _cobrar_efectivo(client, db, cajero_headers, id_pedido, monto):
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [id_pedido],
            "pagos": [{"id_metodo_pago": efectivo, "monto": monto}],
        },
    )
    assert r.status_code == 201
    return r.json()


def _estado_mesa(client, admin_headers, id_mesa):
    return client.get(f"/api/v1/mesas/{id_mesa}", headers=admin_headers).json()["estado"]


def test_cobrar_una_ronda_no_libera_la_mesa_con_otra_activa(
    client, db, admin_headers, cajero_headers
):
    pedido1 = _pedido(client, db, admin_headers, numero=610, precio=116.0)
    pedido2 = _otra_ronda(client, db, admin_headers, pedido1["id_mesa"])
    _cobrar_efectivo(client, db, cajero_headers, pedido1["id_pedido"], 116.0)
    assert _estado_mesa(client, admin_headers, pedido1["id_mesa"]) == "Ocupada"
    _cobrar_efectivo(client, db, cajero_headers, pedido2["id_pedido"], 58.0)
    assert _estado_mesa(client, admin_headers, pedido1["id_mesa"]) == "Disponible"


def test_mesa_se_libera_con_ronda_cobrada_y_ronda_cancelada(
    client, db, admin_headers, cajero_headers
):
    pedido1 = _pedido(client, db, admin_headers, numero=611, precio=116.0)
    pedido2 = _otra_ronda(client, db, admin_headers, pedido1["id_mesa"])
    r = client.post(
        f"/api/v1/pedidos/{pedido1['id_pedido']}/cancelar",
        headers=admin_headers,
        json={"motivo": "Cliente cambió de opinión"},
    )
    assert r.status_code == 200
    assert _estado_mesa(client, admin_headers, pedido1["id_mesa"]) == "Ocupada"
    _cobrar_efectivo(client, db, cajero_headers, pedido2["id_pedido"], 58.0)
    assert _estado_mesa(client, admin_headers, pedido1["id_mesa"]) == "Disponible"


def _entregar(client, db, admin_headers, id_pedido):
    """Avanza un pedido Pendiente hasta Entregado por la API de transiciones."""
    from app.models import EstadoPedido

    for nombre in ("En preparación", "Listo", "Entregado"):
        est = (
            db.query(EstadoPedido)
            .filter(EstadoPedido.nombre_estado == nombre)
            .one()
        )
        r = client.patch(
            f"/api/v1/pedidos/{id_pedido}/estado",
            headers=admin_headers,
            json={"id_estado": est.id_estado},
        )
        assert r.status_code == 200


def test_cobrar_cuenta_de_dos_rondas_201(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=620, precio=116.0)
    ronda2 = _otra_ronda(client, db, admin_headers, pedido["id_mesa"], precio=58.0)
    _entregar(client, db, admin_headers, pedido["id_pedido"])
    _entregar(client, db, admin_headers, ronda2["id_pedido"])
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"], ronda2["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["total"]) == 174.0
    assert float(body["cambio"]) == 26.0
    assert sorted(body["ids_pedidos"]) == sorted(
        [pedido["id_pedido"], ronda2["id_pedido"]]
    )
    assert body["folio"].startswith("V-")
    assert _estado_mesa(client, admin_headers, pedido["id_mesa"]) == "Disponible"


def test_cobrar_cuenta_mesas_distintas_409(client, db, admin_headers, cajero_headers):
    p1 = _pedido(client, db, admin_headers, numero=621)
    p2 = _pedido(client, db, admin_headers, numero=622)
    _entregar(client, db, admin_headers, p1["id_pedido"])
    _entregar(client, db, admin_headers, p2["id_pedido"])
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [p1["id_pedido"], p2["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}],
        },
    )
    assert r.status_code == 409
    assert "misma mesa" in r.json()["detail"]


def test_cobrar_cuenta_con_ronda_sin_entregar_409(
    client, db, admin_headers, cajero_headers
):
    pedido = _pedido(client, db, admin_headers, numero=623)
    ronda2 = _otra_ronda(client, db, admin_headers, pedido["id_mesa"])
    _entregar(client, db, admin_headers, pedido["id_pedido"])  # ronda2 queda Pendiente
    efectivo = _metodo_id(db, "Efectivo")
    ids = [pedido["id_pedido"], ronda2["id_pedido"]]
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={"ids_pedidos": ids, "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}]},
    )
    assert r.status_code == 409
    assert "sin entregar" in r.json()["detail"]
    assert _estado_mesa(client, admin_headers, pedido["id_mesa"]) == "Ocupada"
    # Tras entregar la ronda pendiente, la misma cuenta sí se cobra.
    _entregar(client, db, admin_headers, ronda2["id_pedido"])
    r2 = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={"ids_pedidos": ids, "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}]},
    )
    assert r2.status_code == 201


def test_cobrar_cuenta_con_ronda_ya_cobrada_409(
    client, db, admin_headers, cajero_headers
):
    pedido = _pedido(client, db, admin_headers, numero=624, precio=116.0)
    ronda2 = _otra_ronda(client, db, admin_headers, pedido["id_mesa"])
    _entregar(client, db, admin_headers, pedido["id_pedido"])
    _entregar(client, db, admin_headers, ronda2["id_pedido"])
    efectivo = _metodo_id(db, "Efectivo")
    r1 = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 116.0}],
        },
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"], ronda2["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}],
        },
    )
    assert r2.status_code == 409
    assert "ya fue cobrado" in r2.json()["detail"]


def test_cobrar_dos_rondas_juntas_con_tercera_pendiente_no_libera_la_mesa(
    client, db, admin_headers, cajero_headers
):
    """Pin de `excepto_ids` haciendo trabajo real en el camino multi-pedido:
    las rondas 1 y 2 (Entregadas) se cobran juntas en UNA sola venta mientras
    la ronda 3 sigue Pendiente -> 201 y la mesa debe seguir "Ocupada" (si
    `excepto_ids` solo excluyera la ronda 1, como en el camino de un solo
    pedido, `tiene_pedido_activo` ignoraría también la ronda 2 -- que ya no
    está activa por estar cobrada, así que el resultado sería el mismo; lo
    que realmente se prueba es que la ronda 3, Pendiente y fuera de esta
    cuenta, sigue contando como activa y mantiene la mesa ocupada). Tras
    entregar y cobrar la ronda 3, la mesa sí se libera.
    """
    ronda1 = _pedido(client, db, admin_headers, numero=630, precio=116.0)
    id_mesa = ronda1["id_mesa"]
    ronda2 = _otra_ronda(client, db, admin_headers, id_mesa, precio=58.0)
    ronda3 = _otra_ronda(client, db, admin_headers, id_mesa, precio=30.0)
    _entregar(client, db, admin_headers, ronda1["id_pedido"])
    _entregar(client, db, admin_headers, ronda2["id_pedido"])
    # ronda3 se queda Pendiente a propósito.

    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [ronda1["id_pedido"], ronda2["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
        },
    )
    assert r.status_code == 201
    assert _estado_mesa(client, admin_headers, id_mesa) == "Ocupada"

    _entregar(client, db, admin_headers, ronda3["id_pedido"])
    _cobrar_efectivo(client, db, cajero_headers, ronda3["id_pedido"], 30.0)
    assert _estado_mesa(client, admin_headers, id_mesa) == "Disponible"


def test_cobrar_ids_repetidos_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=625)
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"], pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}],
        },
    )
    assert r.status_code == 422


def test_cobrar_concurrencia_misma_ronda_no_duplica_el_cobro():
    """Pin de la invariante que protege el `SELECT ... FOR UPDATE` en
    `venta_service.cobrar`: sin ese lock, dos transacciones que cobran el
    MISMO pedido concurrentemente pueden ambas leer `id_venta is None` bajo
    READ COMMITTED y ambas pasarían la validación «El pedido ya fue
    cobrado», produciendo una venta huérfana (folio y pagos sin pedido
    real). Este test abre DOS conexiones/transacciones reales e independientes
    contra la BD de test (los fixtures `db`/`client` comparten una sola
    conexión cuya transacción externa nunca se commitea de verdad, así que no
    sirven para probar bloqueo entre transacciones distintas).

    Sesión A simula un cobro en curso: toma el lock de fila con
    `with_for_update` y asigna `pedido.id_venta`, pero SIN hacer commit
    todavía (el estado exacto de `cobrar` entre su `flush()` y su `commit()`
    final). Sesión B llama al `cobrar()` real para el mismo pedido en un
    hilo aparte y debe quedar bloqueada en su propio `db.get(...,
    with_for_update=True)` -- se verifica el bloqueo real consultando
    `pg_stat_activity` (no con un `sleep` fijo, para no ser frágil). Al
    liberar A (commit), B debe desbloquear, releer `id_venta` ya asignado y
    responder 409 «El pedido ya fue cobrado» en vez de cobrar por segunda vez.
    """
    # --- Setup: fila de pedido real y COMMITEADA (conexión propia, fuera de
    # la transacción de rollback de los fixtures) para que sea visible desde
    # las dos conexiones independientes de la carrera.
    setup_conn = _engine.connect()
    setup = OrmSession(bind=setup_conn)
    try:
        cajero = setup.execute(
            select(Usuario).where(Usuario.correo == "cajero@cafeteria.com")
        ).scalar_one()
        mesa = setup.execute(select(Mesa).where(Mesa.numero_mesa == 1)).scalar_one()
        producto = setup.execute(select(Producto)).scalars().first()
        pendiente = setup.execute(
            select(EstadoPedido).where(EstadoPedido.nombre_estado == "Pendiente")
        ).scalar_one()
        efectivo = setup.execute(
            select(MetodoPago).where(MetodoPago.nombre_metodo == "Efectivo")
        ).scalar_one()

        pedido = Pedido(
            id_mesa=mesa.id_mesa,
            id_usuario=cajero.id_usuario,
            id_estado=pendiente.id_estado,
        )
        setup.add(pedido)
        setup.flush()
        setup.add(
            DetallePedido(
                id_pedido=pedido.id_pedido,
                id_producto=producto.id_producto,
                cantidad=1,
                precio_unitario=producto.precio_venta,
            )
        )
        setup.commit()
        id_pedido = pedido.id_pedido
        id_cajero = cajero.id_usuario
        id_efectivo = efectivo.id_metodo_pago
    finally:
        setup.close()
        setup_conn.close()

    conn_a = _engine.connect()
    session_a = OrmSession(bind=conn_a)
    conn_b = _engine.connect()
    session_b = OrmSession(bind=conn_b)
    resultado_b: dict = {}
    id_venta_a: int | None = None

    def _cobrar_b():
        try:
            usuario_b = session_b.get(Usuario, id_cajero)
            data = VentaCreate(
                ids_pedidos=[id_pedido],
                pagos=[PagoIn(id_metodo_pago=id_efectivo, monto=Decimal("500.00"))],
            )
            venta_service.cobrar(session_b, data, usuario_b)
        except HTTPException as exc:
            resultado_b["exc"] = exc
        except Exception as exc:  # pragma: no cover - diagnóstico si algo más falla
            resultado_b["error"] = exc

    try:
        # Sesión A toma el lock y dobla como "cobro en curso" sin commitear.
        usuario_a = session_a.get(Usuario, id_cajero)
        pedido_a = session_a.execute(
            select(Pedido).where(Pedido.id_pedido == id_pedido).with_for_update(of=Pedido)
        ).scalar_one()
        venta_a = Venta(id_usuario=usuario_a.id_usuario, total=pedido_a.total)
        session_a.add(venta_a)
        session_a.flush()
        pedido_a.id_venta = venta_a.id_venta
        id_venta_a = venta_a.id_venta

        pid_b = session_b.execute(text("SELECT pg_backend_pid()")).scalar()

        hilo_b = threading.Thread(target=_cobrar_b, daemon=True)
        hilo_b.start()

        # Verificación robusta de bloqueo real (sondeo con tope de tiempo, no
        # un sleep fijo): B debe aparecer esperando un lock en pg_stat_activity.
        bloqueada = False
        limite = time.monotonic() + 5.0
        with _engine.connect() as monitor_conn:
            while time.monotonic() < limite:
                fila = monitor_conn.execute(
                    text(
                        "SELECT wait_event_type FROM pg_stat_activity WHERE pid = :pid"
                    ),
                    {"pid": pid_b},
                ).first()
                if fila and fila[0] == "Lock":
                    bloqueada = True
                    break
                time.sleep(0.02)
        assert bloqueada, "La sesión B debía quedar bloqueada esperando el lock de fila"
        assert hilo_b.is_alive()

        # A libera el lock: su cobro queda finalizado de verdad.
        session_a.commit()

        hilo_b.join(timeout=5)
        assert not hilo_b.is_alive(), "La sesión B no terminó tras liberarse el lock"
        exc = resultado_b.get("exc")
        assert exc is not None, resultado_b.get("error")
        assert exc.status_code == 409
        assert "ya fue cobrado" in exc.detail
    finally:
        session_b.close()
        conn_b.close()
        session_a.close()
        conn_a.close()
        # Limpieza: estos datos quedaron commiteados de verdad (conexiones
        # propias, fuera de la transacción de rollback de los fixtures).
        cleanup_conn = _engine.connect()
        try:
            if id_venta_a is not None:
                cleanup_conn.execute(
                    text("DELETE FROM pagos WHERE id_venta = :v"), {"v": id_venta_a}
                )
                cleanup_conn.execute(
                    text("DELETE FROM tickets WHERE id_venta = :v"), {"v": id_venta_a}
                )
            cleanup_conn.execute(
                text("DELETE FROM detalle_pedido WHERE id_pedido = :p"),
                {"p": id_pedido},
            )
            cleanup_conn.execute(
                text("DELETE FROM pedidos WHERE id_pedido = :p"), {"p": id_pedido}
            )
            if id_venta_a is not None:
                cleanup_conn.execute(
                    text("DELETE FROM ventas WHERE id_venta = :v"), {"v": id_venta_a}
                )
            cleanup_conn.commit()
        finally:
            cleanup_conn.close()
