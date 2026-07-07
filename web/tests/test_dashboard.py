import datetime
import json
import re

from app.dashboard.routes import (
    _bucketizar_mensual,
    _serie_ventas_vs_gastos,
    rango_preset,
)
from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
COMPARATIVO = {
    "actual": {
        "total_vendido": 400.0, "num_ventas": 2, "ticket_promedio": 200.0,
        "total_gastos": 50.0, "total_compras": 100.0, "utilidad_estimada": 250.0,
    },
    "anterior": {
        "total_vendido": 360.0, "num_ventas": 2, "ticket_promedio": 180.0,
        "total_gastos": 40.0, "total_compras": 90.0, "utilidad_estimada": 230.0,
    },
    "deltas": {
        "total_vendido": 11.1, "total_gastos": 25.0,
        "utilidad_estimada": 8.7, "num_ventas": 0.0,
    },
}
# OJO: la API serializa Decimal como STRING en JSON (p.ej. "400.00"); los stubs
# deben reflejarlo para no divergir del contrato real (una divergencia float
# ocultó un TypeError en el helper acumulador).
SERIE = [{"fecha": "2026-07-05", "total": "400.00", "num_ventas": 2}]
# Incluye 2026-07-06, fecha ausente en SERIE, para probar la alineación con 0.
GASTOS_SERIE = [
    {"fecha": "2026-07-05", "total": "50.00", "num_gastos": 1},
    {"fecha": "2026-07-06", "total": "30.00", "num_gastos": 1},
]
TOP = [{"id_producto": 1, "nombre": "Café", "cantidad": 5, "importe": 150.0}]
INVENTARIO = [
    {"nombre": "Café en grano", "unidad": "kg", "stock_actual": 2.0,
     "stock_minimo": 5.0, "nivel_pct": 20, "bajo_minimo": True},
    {"nombre": "Leche", "unidad": "L", "stock_actual": 8.0,
     "stock_minimo": 4.0, "nivel_pct": 100, "bajo_minimo": False},
]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "x"})


def _stub_reportes(monkeypatch):
    monkeypatch.setattr(api_client, "get_comparativo", lambda a, d, h: COMPARATIVO)
    monkeypatch.setattr(api_client, "get_ventas_por_dia", lambda a, d, h: SERIE)
    monkeypatch.setattr(api_client, "get_gastos_por_dia", lambda a, d, h: GASTOS_SERIE)
    monkeypatch.setattr(api_client, "get_top_productos", lambda a, d, h: TOP)
    monkeypatch.setattr(api_client, "get_inventario_niveles", lambda a: INVENTARIO)


def test_dashboard_sin_sesion_redirige(client):
    r = client.get("/dashboard")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_dashboard_muestra_kpis(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    r = client.get("/dashboard")
    assert r.status_code == 200
    cuerpo = r.get_data(as_text=True)
    assert "$400.00" in cuerpo      # total vendido
    assert "Utilidad" in cuerpo     # tarjeta de utilidad estimada


def test_index_redirige_a_dashboard(client, monkeypatch):
    _login(client, monkeypatch)
    r = client.get("/")
    assert r.status_code == 302
    assert "/dashboard" in r.headers["Location"]


def test_dashboard_incluye_graficas(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    r = client.get("/dashboard")
    cuerpo = r.get_data(as_text=True)
    assert 'id="chart-ventas"' in cuerpo
    assert 'id="chart-top"' in cuerpo
    assert "chart.umd.min.js" in cuerpo
    assert "Café" in cuerpo          # dato del top embebido en el JSON


def test_dashboard_ventas_vs_gastos(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    r = client.get("/dashboard")
    assert r.status_code == 200
    cuerpo = r.get_data(as_text=True)
    assert "Ventas vs Gastos" in cuerpo
    assert '"Ventas"' in cuerpo
    assert '"Gastos"' in cuerpo
    # el color debe ir atado a su dataset: Ventas = café oscuro, Gastos = mostaza
    # (si se intercambiaran los colores, estas dos aserciones fallarían).
    import re
    assert re.search(r'label:\s*"Ventas"[^}]*?backgroundColor:\s*"#3a2a20"', cuerpo)
    assert re.search(r'label:\s*"Gastos"[^}]*?backgroundColor:\s*"#c8862f"', cuerpo)
    # alineación por fecha: 2026-07-06 solo tiene gasto, debe aparecer en serie_vg
    assert "2026-07-06" in cuerpo


def test_serie_ventas_vs_gastos_alinea_fechas_con_ceros():
    # Totales como STRING (como los envía la API real, Decimal->JSON string).
    serie = [
        {"fecha": "2026-07-04", "total": "100.00", "num_ventas": 1},
        {"fecha": "2026-07-05", "total": "400.00", "num_ventas": 2},
    ]
    gastos = [
        {"fecha": "2026-07-05", "total": "50.00", "num_gastos": 1},
        {"fecha": "2026-07-06", "total": "30.00", "num_gastos": 1},
    ]
    resultado = _serie_ventas_vs_gastos(serie, gastos)
    assert resultado == [
        {"fecha": "2026-07-04", "ventas": 100.0, "gastos": 0},
        {"fecha": "2026-07-05", "ventas": 400.0, "gastos": 50.0},
        {"fecha": "2026-07-06", "ventas": 0, "gastos": 30.0},
    ]


def test_serie_ventas_vs_gastos_acumula_fechas_duplicadas():
    # La API contempla una fila por día, pero ante una fecha duplicada
    # (p.ej. reintento/paginación) los totales deben sumarse, no perderse.
    serie = [
        {"fecha": "2026-07-05", "total": "400.00", "num_ventas": 2},
        {"fecha": "2026-07-05", "total": "100.00", "num_ventas": 1},
    ]
    gastos = [
        {"fecha": "2026-07-05", "total": "50.00", "num_gastos": 1},
        {"fecha": "2026-07-05", "total": "30.00", "num_gastos": 1},
    ]
    resultado = _serie_ventas_vs_gastos(serie, gastos)
    assert resultado == [
        {"fecha": "2026-07-05", "ventas": 500.0, "gastos": 80.0},
    ]


def test_dashboard_dona_tendencia_e_inventario(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    assert "doughnut" in cuerpo               # tipo de la dona
    assert 'id="chart-pedidos"' in cuerpo     # línea de tendencia
    assert "Café en grano" in cuerpo          # barra de inventario
    assert "20%" in cuerpo                     # nivel_pct de la barra


def test_dashboard_dona_total_central_plugin(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    # Plugin inline de texto central: debe usar un hook de dibujo real sobre el
    # canvas (no un overlay CSS) y escribir la etiqueta "pedidos" con fillText.
    assert "afterDraw" in cuerpo or "beforeDraw" in cuerpo
    assert "fillText(" in cuerpo
    assert '"pedidos"' in cuerpo
    # se registra SOLO para la dona (array plugins local a esa gráfica, no Chart.register)
    assert "plugins: [centerTextPlugin]" in cuerpo
    assert "Chart.register" not in cuerpo


def test_dashboard_dona_leyenda_con_porcentaje(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    assert "generateLabels" in cuerpo
    # concatenación del texto de la etiqueta con el porcentaje calculado
    assert '`${item.text} ${pct}%`' in cuerpo


def test_dashboard_tendencia_gradiente(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    assert "createLinearGradient(" in cuerpo
    # guard obligatorio anclado a la tendencia: devuelve el tono crema base
    # (distinto del guard "return;" a secas del plugin de la dona).
    assert 'if (!chartArea) return "rgba(217,201,187,0.25)"' in cuerpo
    # el relleno crema se difumina de opaco a transparente
    assert 'rgba(217,201,187,0.55)' in cuerpo
    assert 'rgba(217,201,187,0)' in cuerpo


def test_dashboard_graficas_tienen_contenedor_con_altura(client, monkeypatch):
    # Chart.js `responsive` colapsa el canvas a 0 (gráfica en blanco) si el
    # contenedor no tiene altura definida. Los 3 canvas deben ir envueltos en
    # `.chart-box` (altura fija en CSS) y usar maintainAspectRatio:false.
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    assert cuerpo.count('class="chart-box"') == 3
    assert cuerpo.count("maintainAspectRatio: false") == 3


def test_dashboard_js_no_declara_globales_reservados(client, monkeypatch):
    # Declarar `const/let/var top` (o name/parent/self/location/…) en el scope
    # global de un <script> clásico choca con la propiedad no-configurable de
    # window y lanza "Identifier 'top' has already been declared", abortando
    # TODO el script -> gráficas en blanco. node --check NO lo detecta (es
    # válido sintácticamente; solo truena en el navegador). Guard de lint.
    import re

    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    reservados = (
        "top", "parent", "self", "name", "location", "length",
        "closed", "frames", "origin", "status", "window",
    )
    patron = re.compile(
        r"\b(?:const|let|var)\s+(" + "|".join(reservados) + r")\b"
    )
    encontrados = patron.findall(cuerpo)
    assert not encontrados, f"nombres globales reservados declarados: {encontrados}"


def test_rango_preset_7dias():
    hoy = datetime.date.today()
    desde, hasta = rango_preset("7dias", None, None)
    assert hasta == hoy.isoformat()
    assert desde == (hoy - datetime.timedelta(days=6)).isoformat()


def test_rango_preset_mes():
    hoy = datetime.date.today()
    desde, hasta = rango_preset("mes", None, None)
    assert desde == hoy.replace(day=1).isoformat()
    assert hasta == hoy.isoformat()


def test_rango_preset_rango_explicito():
    assert rango_preset("rango", "2026-06-01", "2026-06-30") == (
        "2026-06-01", "2026-06-30",
    )


def test_rango_preset_hoy_y_desconocido():
    hoy = datetime.date.today()
    # "hoy" se mantiene funcionando por compatibilidad (ya no es el default,
    # pero sigue siendo un preset válido si se solicita explícitamente).
    assert rango_preset("hoy", None, None) == (hoy.isoformat(), hoy.isoformat())
    # Un preset desconocido/None ahora cae al default sensato "mes" (no "hoy").
    assert rango_preset("otro", None, None) == (
        hoy.replace(day=1).isoformat(), hoy.isoformat(),
    )


def _fijar_hoy(monkeypatch, y, m, d):
    """Fija date.today() en la ruta a una fecha conocida (para probar la
    aritmética de meses con valores esperados HARDCODEADOS, independientes de
    la fórmula de la implementación — si no, el test sería una tautología)."""
    import app.dashboard.routes as routes

    class _FakeDate(datetime.date):
        @classmethod
        def today(cls):
            return datetime.date(y, m, d)

    monkeypatch.setattr(routes, "date", _FakeDate)


def test_rango_preset_6meses_cruza_anio_desde_febrero(monkeypatch):
    # Hoy = 15-feb-2026; 5 meses atrás (6 naturales inclusive) = sep-2025.
    _fijar_hoy(monkeypatch, 2026, 2, 15)
    assert rango_preset("6meses", None, None) == ("2025-09-01", "2026-02-15")


def test_rango_preset_6meses_cruza_anio_desde_enero(monkeypatch):
    # Hoy = 10-ene-2026; 5 meses atrás = ago-2025.
    _fijar_hoy(monkeypatch, 2026, 1, 10)
    assert rango_preset("6meses", None, None) == ("2025-08-01", "2026-01-10")


def test_rango_preset_6meses_mismo_anio(monkeypatch):
    # Hoy = 20-jul-2026; 5 meses atrás = feb-2026 (sin cruzar año).
    _fijar_hoy(monkeypatch, 2026, 7, 20)
    assert rango_preset("6meses", None, None) == ("2026-02-01", "2026-07-20")


def test_rango_preset_anio():
    hoy = datetime.date.today()
    desde, hasta = rango_preset("anio", None, None)
    assert desde == hoy.replace(month=1, day=1).isoformat()
    assert hasta == hoy.isoformat()


def test_bucketizar_mensual_agrupa_y_suma_por_mes():
    # Serie diaria que cruza 2 meses (mayo -> junio); debe agrupar por
    # "YYYY-MM", sumar ventas/gastos numéricamente y quedar ordenada.
    serie_vg = [
        {"fecha": "2026-05-30", "ventas": 100.0, "gastos": 20.0},
        {"fecha": "2026-05-31", "ventas": 50.0, "gastos": 10.0},
        {"fecha": "2026-06-01", "ventas": 200.0, "gastos": 30.0},
    ]
    resultado = _bucketizar_mensual(serie_vg)
    assert resultado == [
        {"fecha": "2026-05", "ventas": 150.0, "gastos": 30.0},
        {"fecha": "2026-06", "ventas": 200.0, "gastos": 30.0},
    ]


def test_dashboard_preset_6meses_bucketiza_serie_vg_por_mes(client, monkeypatch):
    # Integración: con preset "6meses" la ruta debe responder 200 y el
    # serie_vg inyectado en el template debe llevar etiquetas mensuales
    # ("YYYY-MM"), no diarias, aunque las series crudas vengan por día.
    _login(client, monkeypatch)
    serie_multimes = [
        {"fecha": "2026-05-15", "total": "100.00", "num_ventas": 1},
        {"fecha": "2026-06-10", "total": "200.00", "num_ventas": 2},
    ]
    gastos_multimes = [
        {"fecha": "2026-05-20", "total": "30.00", "num_gastos": 1},
        {"fecha": "2026-06-15", "total": "40.00", "num_gastos": 1},
    ]
    monkeypatch.setattr(api_client, "get_comparativo", lambda a, d, h: COMPARATIVO)
    monkeypatch.setattr(
        api_client, "get_ventas_por_dia", lambda a, d, h: serie_multimes
    )
    monkeypatch.setattr(
        api_client, "get_gastos_por_dia", lambda a, d, h: gastos_multimes
    )
    monkeypatch.setattr(api_client, "get_top_productos", lambda a, d, h: TOP)
    monkeypatch.setattr(api_client, "get_inventario_niveles", lambda a: INVENTARIO)

    r = client.get("/dashboard?preset=6meses")
    assert r.status_code == 200
    cuerpo = r.get_data(as_text=True)

    match = re.search(r'<script id="vg-data"[^>]*>(.*?)</script>', cuerpo, re.S)
    datos_vg = json.loads(match.group(1))
    fechas = [p["fecha"] for p in datos_vg]
    assert fechas == ["2026-05", "2026-06"]
    assert all(len(f) == 7 for f in fechas)  # "YYYY-MM", no "YYYY-MM-DD"

    # la tendencia (serie diaria) NO se bucketiza: sigue trayendo fechas diarias
    match_serie = re.search(r'<script id="serie-data"[^>]*>(.*?)</script>', cuerpo, re.S)
    datos_serie = json.loads(match_serie.group(1))
    assert [p["fecha"] for p in datos_serie] == ["2026-05-15", "2026-06-10"]


def test_dashboard_preset_mes_mantiene_serie_vg_diaria(client, monkeypatch):
    # Preset "mes" (y "rango") deben conservar la granularidad diaria.
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    r = client.get("/dashboard?preset=mes")
    assert r.status_code == 200
    cuerpo = r.get_data(as_text=True)
    match = re.search(r'<script id="vg-data"[^>]*>(.*?)</script>', cuerpo, re.S)
    datos_vg = json.loads(match.group(1))
    assert any(len(p["fecha"]) == 10 for p in datos_vg)  # "YYYY-MM-DD"


def test_dashboard_delta_gastos_positivo_es_down(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    # Gastos subió (+25%) => alerta => clase "down" (rojo), no "up".
    import re
    bloque = re.search(r'Gastos.*?kpi__delta--(\w+)', cuerpo, re.S).group(1)
    assert bloque == "down"


def test_dashboard_delta_ventas_positivo_es_up(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    import re
    bloque = re.search(r'Total vendido.*?kpi__delta--(\w+)', cuerpo, re.S).group(1)
    assert bloque == "up"
