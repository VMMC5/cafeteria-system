import datetime

from app.dashboard.routes import rango_preset
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
SERIE = [{"fecha": "2026-07-05", "total": 400.0, "num_ventas": 2}]
TOP = [{"id_producto": 1, "nombre": "Café", "cantidad": 5, "importe": 150.0}]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "x"})


def _stub_reportes(monkeypatch):
    monkeypatch.setattr(api_client, "get_comparativo", lambda a, d, h: COMPARATIVO)
    monkeypatch.setattr(api_client, "get_ventas_por_dia", lambda a, d, h: SERIE)
    monkeypatch.setattr(api_client, "get_top_productos", lambda a, d, h: TOP)


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
    assert rango_preset("hoy", None, None) == (hoy.isoformat(), hoy.isoformat())
    assert rango_preset("otro", None, None) == (hoy.isoformat(), hoy.isoformat())


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
