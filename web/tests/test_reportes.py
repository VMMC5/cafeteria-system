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
    # El enlace del sidebar renderiza href="{{ url_for('reportes.index') }}" -> /reportes.
    # Verificamos el ancla real, no solo el texto "Reportes" (presente también en <title>/<h1>).
    assert 'href="/reportes"' in cuerpo


XLSX_CT = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def test_reportes_export_xlsx(client, monkeypatch):
    _login(client, monkeypatch)
    _stub(monkeypatch)
    r = client.get("/reportes?tipo=ventas&preset=rango&desde=2026-07-01&hasta=2026-07-31&formato=xlsx")
    assert r.status_code == 200
    assert r.mimetype == XLSX_CT
    assert "attachment" in r.headers["Content-Disposition"]
    assert r.data[:2] == b"PK"  # los .xlsx son ZIP


def test_reportes_export_pdf(client, monkeypatch):
    _login(client, monkeypatch)
    _stub(monkeypatch)
    r = client.get("/reportes?tipo=ventas&preset=rango&desde=2026-07-01&hasta=2026-07-31&formato=pdf")
    assert r.status_code == 200
    assert r.mimetype == "application/pdf"
    assert "attachment" in r.headers["Content-Disposition"]
    assert r.data[:4] == b"%PDF"


def test_reportes_xlsx_celdas_numericas(client, monkeypatch):
    _login(client, monkeypatch)
    _stub(monkeypatch)
    from io import BytesIO
    from openpyxl import load_workbook
    r = client.get("/reportes?tipo=ventas&preset=rango&desde=2026-07-01&hasta=2026-07-31&formato=xlsx")
    ws = load_workbook(BytesIO(r.data)).active
    # data row 2, "Total" column (4th) must be a real number, not "232.00"
    assert ws.cell(row=2, column=4).value == 232.0
    assert isinstance(ws.cell(row=2, column=4).value, (int, float))
