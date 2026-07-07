from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
VENTAS = [{"folio": "V-0001", "fecha": "2026-07-05T12:00:00Z", "mesa": 3,
           "total": 232.0, "metodos": "Efectivo"}]
GASTOS = [{"fecha": "2026-07-05T09:00:00Z", "categoria": "Servicios",
           "concepto": "Luz", "monto": 250.0}]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "x"})


def _stub(monkeypatch):
    monkeypatch.setattr(api_client, "get_reporte_ventas", lambda a, d, h: VENTAS)
    monkeypatch.setattr(api_client, "get_reporte_gastos", lambda a, d, h: GASTOS)


def test_reportes_sin_sesion_redirige(client):
    r = client.get("/reportes")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_reportes_preview_ventas(client, monkeypatch):
    _login(client, monkeypatch)
    _stub(monkeypatch)
    cuerpo = client.get("/reportes?tipo=ventas").get_data(as_text=True)
    assert "V-0001" in cuerpo
    assert "Efectivo" in cuerpo
    assert "Reporte de Ventas" in cuerpo


def test_reportes_preview_gastos(client, monkeypatch):
    _login(client, monkeypatch)
    _stub(monkeypatch)
    cuerpo = client.get("/reportes?tipo=gastos").get_data(as_text=True)
    assert "Luz" in cuerpo
    assert "Reporte de Gastos" in cuerpo


def test_sidebar_incluye_reportes(client, monkeypatch):
    _login(client, monkeypatch)
    _stub(monkeypatch)
    cuerpo = client.get("/reportes?tipo=ventas").get_data(as_text=True)
    assert "Reportes" in cuerpo
