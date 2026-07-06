from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
RESUMEN = {
    "total_vendido": 400.0, "num_ventas": 2, "ticket_promedio": 200.0,
    "total_gastos": 50.0, "total_compras": 100.0, "utilidad_estimada": 250.0,
}
SERIE = [{"fecha": "2026-07-05", "total": 400.0, "num_ventas": 2}]
TOP = [{"id_producto": 1, "nombre": "Café", "cantidad": 5, "importe": 150.0}]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "x"})


def _stub_reportes(monkeypatch):
    monkeypatch.setattr(api_client, "get_reporte_resumen", lambda a, d, h: RESUMEN)
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
    assert "400" in cuerpo          # total vendido
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
