# Sprint 6 · Slice B — Reportes filtrables + export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir endpoints de detalle de ventas/gastos en la API y una página web `/reportes` con vista previa y descarga en PDF (WeasyPrint) y XLSX (openpyxl).

**Architecture:** Opción A — la API lista el detalle (`/reportes/ventas`, `/reportes/gastos`, solo Admin); el panel web (cliente delgado) pinta la vista previa y genera los archivos. Una sola página `/reportes` con selector de tipo. Sin migraciones. Trabajo **local** (rama `feature/sprint6-backlog`, commits locales, **sin push/PR**).

**Tech Stack:** FastAPI + SQLAlchemy (backend); Flask + Jinja2 + openpyxl + WeasyPrint (web); pytest.

## Global Constraints

- **Trabajo local:** commits locales en `feature/sprint6-backlog`. NO `git push`, NO PRs.
- **Sin migraciones**; solo lectura sobre tablas existentes.
- **Autorización:** `GET /reportes/*` con `Depends(deps.require_admin)` (403 no-admin, 401 sin token). Rutas web con `@login_required`.
- **Fechas:** query `desde`/`hasta` tipo `date`, ambos inclusive, default hoy; filtro `func.date(col)` BETWEEN. Reutiliza `reporte_service.rango`.
- **Ventas:** solo `Venta.estado_venta == "Completada"`.
- **Contrato ventas:** `[{folio, fecha, mesa, total, metodos}]` — folio del ticket; mesa = `numero_mesa` del pedido; metodos = nombres de método de pago concatenados (pago dividido).
- **Contrato gastos:** `[{fecha, categoria, concepto, monto}]` — categoria = `nombre_categoria`.
- **Export:** XLSX con `Content-Type application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`; PDF con `application/pdf`; ambos `Content-Disposition: attachment`.
- **Tests:** backend `docker compose exec api pytest`; web `docker compose exec web pytest`.
- **Money como Decimal** en los schemas (igual que `GastoOut`).

---

## File Structure

**Backend (modificar):**
- `backend/app/schemas/reporte.py` — `+ VentaDetalleOut`, `+ GastoDetalleOut`.
- `backend/app/services/reporte_service.py` — `+ detalle_ventas`, `+ detalle_gastos`.
- `backend/app/api/v1/reportes.py` — `+ GET /reportes/ventas`, `+ GET /reportes/gastos`.
- `backend/tests/test_reportes_api.py` — tests de detalle.

**Web (crear):**
- `web/app/reportes/__init__.py` (paquete vacío).
- `web/app/reportes/routes.py` — blueprint `reportes` (`/reportes`) + helper `_reporte`.
- `web/app/services/export.py` — `to_xlsx`, `to_pdf`.
- `web/app/templates/reportes/index.html` — config + vista previa.
- `web/app/templates/reportes/print.html` — plantilla de impresión (fuente del PDF).
- `web/tests/test_reportes.py` — tests de la página y el export.

**Web (modificar):**
- `web/requirements.txt` — `+ openpyxl`, `+ WeasyPrint`.
- `web/Dockerfile` — libs nativas de WeasyPrint.
- `web/app/services/api_client.py` — `+ get_reporte_ventas`, `+ get_reporte_gastos`.
- `web/app/__init__.py` — registrar blueprint `reportes`.
- `web/app/templates/base.html` — enlace "Reportes" en el sidebar.

---

## Task 1: API — detalle de ventas y gastos

**Files:**
- Modify: `backend/app/schemas/reporte.py`
- Modify: `backend/app/services/reporte_service.py`
- Modify: `backend/app/api/v1/reportes.py`
- Test: `backend/tests/test_reportes_api.py`

**Interfaces:**
- Consumes: `reporte_service.rango`; helper `_cobrar(client, db, admin_headers, cajero_headers, numero, precio=...)` ya existente en el test (crea mesa+producto+pedido y lo cobra, devuelve la venta con `folio`).
- Produces:
  - `reporte_service.detalle_ventas(db, desde, hasta) -> list[dict]` con `{folio: str, fecha: datetime, mesa: int|None, total: Decimal, metodos: str}`.
  - `reporte_service.detalle_gastos(db, desde, hasta) -> list[dict]` con `{fecha: datetime, categoria: str, concepto: str, monto: Decimal}`.
  - Endpoints `GET /api/v1/reportes/ventas` y `GET /api/v1/reportes/gastos` (solo Admin).

- [ ] **Step 1: Write the failing tests**

Añadir a `backend/tests/test_reportes_api.py`:

```python
def _gasto(db, admin, monto, concepto="Luz"):
    from app.models import CategoriaGasto, Gasto

    cat = db.query(CategoriaGasto).first()
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec api pytest tests/test_reportes_api.py -k "detalle" -v`
Expected: FAIL — 404 (endpoints no existen).

- [ ] **Step 3: Add the schemas**

En `backend/app/schemas/reporte.py`, cambiar la primera línea de import y añadir dos schemas al final:

```python
from datetime import date, datetime
```

```python
class VentaDetalleOut(BaseModel):
    folio: str
    fecha: datetime
    mesa: int | None
    total: Decimal
    metodos: str


class GastoDetalleOut(BaseModel):
    fecha: datetime
    categoria: str
    concepto: str
    monto: Decimal
```

- [ ] **Step 4: Add the service functions**

Añadir a `backend/app/services/reporte_service.py`:

```python
def detalle_ventas(db: Session, desde: date, hasta: date) -> list[dict]:
    ventas = (
        db.query(Venta)
        .filter(
            func.date(Venta.fecha_venta) >= desde,
            func.date(Venta.fecha_venta) <= hasta,
            Venta.estado_venta == "Completada",
        )
        .order_by(Venta.fecha_venta)
        .all()
    )
    out = []
    for v in ventas:
        pedido = db.get(Pedido, v.id_pedido)
        metodos = ", ".join(sorted({p.metodo.nombre_metodo for p in v.pagos}))
        out.append(
            {
                "folio": v.ticket.folio if v.ticket else "",
                "fecha": v.fecha_venta,
                "mesa": pedido.mesa.numero_mesa if pedido and pedido.mesa else None,
                "total": v.total,
                "metodos": metodos,
            }
        )
    return out


def detalle_gastos(db: Session, desde: date, hasta: date) -> list[dict]:
    gastos = (
        db.query(Gasto)
        .filter(
            func.date(Gasto.fecha_gasto) >= desde,
            func.date(Gasto.fecha_gasto) <= hasta,
        )
        .order_by(Gasto.fecha_gasto)
        .all()
    )
    return [
        {
            "fecha": g.fecha_gasto,
            "categoria": g.categoria.nombre_categoria,
            "concepto": g.concepto,
            "monto": g.monto,
        }
        for g in gastos
    ]
```

- [ ] **Step 5: Add the endpoints**

En `backend/app/api/v1/reportes.py`, actualizar el import de schemas y añadir dos endpoints:

```python
from app.schemas.reporte import (
    GastoDetalleOut,
    ResumenOut,
    TopProductoOut,
    VentaDetalleOut,
    VentaPorDiaOut,
)
```

```python
@router.get("/ventas", response_model=list[VentaDetalleOut])
def detalle_ventas(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.detalle_ventas(db, d, h)


@router.get("/gastos", response_model=list[GastoDetalleOut])
def detalle_gastos(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.detalle_gastos(db, d, h)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose exec api pytest tests/test_reportes_api.py -v`
Expected: PASS (todos, incluidos los nuevos de detalle).

- [ ] **Step 7: Full backend suite**

Run: `docker compose exec api pytest`
Expected: PASS (sin regresiones).

- [ ] **Step 8: Commit (local)**

```bash
git add backend/app/schemas/reporte.py backend/app/services/reporte_service.py \
        backend/app/api/v1/reportes.py backend/tests/test_reportes_api.py
git commit -m "feat(api): reportes detalle de ventas y gastos"
```

---

## Task 2: Web — dependencias de export + Dockerfile

**Files:**
- Modify: `web/requirements.txt`
- Modify: `web/Dockerfile`

**Interfaces:**
- Produces: la imagen `web` con `openpyxl` y `WeasyPrint` (y sus libs nativas) importables.

- [ ] **Step 1: Add the Python deps**

Añadir al final de `web/requirements.txt`:

```
openpyxl==3.1.5
WeasyPrint==62.3
```

- [ ] **Step 2: Add native libs to the Dockerfile**

En `web/Dockerfile`, insertar un `apt-get` **antes** del `RUN pip install`:

```dockerfile
FROM python:3.12-slim
WORKDIR /code
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangocairo-1.0-0 libcairo2 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["gunicorn", "-b", "0.0.0.0:5000", "run:app"]
```

- [ ] **Step 3: Rebuild the web image and restart**

Run:
```bash
docker compose build web && docker compose up -d web
```
Expected: build OK, contenedor `web` levantado.

- [ ] **Step 4: Verify the libs import inside the container**

Run: `docker compose exec -T web python -c "import weasyprint, openpyxl; print('ok')"`
Expected: prints `ok` (sin ImportError ni error de libs nativas).

- [ ] **Step 5: Full web suite still green**

Run: `docker compose exec web pytest`
Expected: PASS (los tests actuales siguen verdes en la nueva imagen).

- [ ] **Step 6: Commit (local)**

```bash
git add web/requirements.txt web/Dockerfile
git commit -m "build(web): WeasyPrint + openpyxl y libs nativas para export"
```

---

## Task 3: Web — página /reportes (vista previa)

**Files:**
- Modify: `web/app/services/api_client.py`
- Create: `web/app/reportes/__init__.py`
- Create: `web/app/reportes/routes.py`
- Create: `web/app/templates/reportes/index.html`
- Modify: `web/app/__init__.py`
- Modify: `web/app/templates/base.html`
- Test: `web/tests/test_reportes.py`

**Interfaces:**
- Consumes: `api_gateway.call`; `rango_preset` de `app.dashboard.routes`.
- Produces:
  - `api_client.get_reporte_ventas(access, desde, hasta) -> list[dict]`, `api_client.get_reporte_gastos(access, desde, hasta) -> list[dict]`.
  - Blueprint `reportes` con endpoint `reportes.index` en `/reportes`.
  - Helper `reportes.routes._reporte(tipo, filas) -> (titulo, headers, rows, total_row)` — usado por vista previa y (Task 4) export.

- [ ] **Step 1: Write the failing test**

Crear `web/tests/test_reportes.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_reportes.py -v`
Expected: FAIL — 404 en `/reportes`.

- [ ] **Step 3: Add API client functions**

Añadir a `web/app/services/api_client.py`:

```python
def get_reporte_ventas(access, desde=None, hasta=None):
    r = requests.get(
        f"{_base()}/reportes/ventas",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta},
        timeout=TIMEOUT,
    )
    return _check(r)


def get_reporte_gastos(access, desde=None, hasta=None):
    r = requests.get(
        f"{_base()}/reportes/gastos",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta},
        timeout=TIMEOUT,
    )
    return _check(r)
```

- [ ] **Step 4: Create the blueprint with the shared `_reporte` helper**

Crear `web/app/reportes/__init__.py` vacío y `web/app/reportes/routes.py`:

```python
from flask import Blueprint, render_template, request
from flask_login import login_required

from app.dashboard.routes import rango_preset
from app.services import api_client, api_gateway

bp = Blueprint("reportes", __name__)


def _reporte(tipo, filas):
    """Normaliza un reporte a (titulo, headers, rows, total_row) para preview/export."""
    if tipo == "gastos":
        headers = ["Fecha", "Categoría", "Concepto", "Monto"]
        rows = [
            [f["fecha"][:10], f["categoria"], f["concepto"], f"{float(f['monto']):.2f}"]
            for f in filas
        ]
        total = sum(float(f["monto"]) for f in filas)
        return "Reporte de Gastos", headers, rows, ["Total", "", "", f"{total:.2f}"]
    headers = ["Folio", "Fecha", "Mesa", "Total", "Métodos"]
    rows = [
        [
            f["folio"],
            f["fecha"][:10],
            "" if f["mesa"] is None else str(f["mesa"]),
            f"{float(f['total']):.2f}",
            f["metodos"],
        ]
        for f in filas
    ]
    total = sum(float(f["total"]) for f in filas)
    return "Reporte de Ventas", headers, rows, ["Total", "", "", f"{total:.2f}", ""]


@bp.route("/reportes")
@login_required
def index():
    tipo = "gastos" if request.args.get("tipo") == "gastos" else "ventas"
    preset = request.args.get("preset", "mes")
    desde, hasta = rango_preset(
        preset, request.args.get("desde"), request.args.get("hasta")
    )
    if tipo == "gastos":
        filas = api_gateway.call(api_client.get_reporte_gastos, desde, hasta)
    else:
        filas = api_gateway.call(api_client.get_reporte_ventas, desde, hasta)
    titulo, headers, rows, total_row = _reporte(tipo, filas)
    return render_template(
        "reportes/index.html",
        tipo=tipo, titulo=titulo, headers=headers, rows=rows, total_row=total_row,
        preset=preset, desde=desde, hasta=hasta,
    )
```

- [ ] **Step 5: Create the preview template**

Crear `web/app/templates/reportes/index.html`:

```html
{% extends "base.html" %}
{% block title %}Reportes — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>Reportes</h1>
    <p class="sub">Genera y descarga reportes en PDF o XLSX</p>
  </div>
</div>

<div class="cols">
  <div class="card">
    <h2 class="card__title">Configurar reporte</h2>
    <form method="get">
      <label>Tipo de reporte
        <select name="tipo" onchange="this.form.submit()">
          <option value="ventas" {{ 'selected' if tipo == 'ventas' }}>Ventas</option>
          <option value="gastos" {{ 'selected' if tipo == 'gastos' }}>Gastos</option>
        </select>
      </label>
      <div class="filtros" style="margin-top:.75rem;">
        <button type="submit" name="preset" value="hoy"   class="pill {{ 'active' if preset == 'hoy' }}">Hoy</button>
        <button type="submit" name="preset" value="7dias" class="pill {{ 'active' if preset == '7dias' }}">7 días</button>
        <button type="submit" name="preset" value="mes"   class="pill {{ 'active' if preset == 'mes' }}">Este mes</button>
      </div>
      <label>Desde <input type="date" name="desde" value="{{ desde }}"></label>
      <label>Hasta <input type="date" name="hasta" value="{{ hasta }}"></label>
      <button type="submit" name="preset" value="rango" class="btn">Aplicar rango</button>
    </form>
    <div style="margin-top:1rem;display:flex;gap:.5rem;flex-wrap:wrap;">
      <a class="btn btn--ghost" href="{{ url_for('reportes.index', tipo=tipo, preset='rango', desde=desde, hasta=hasta, formato='pdf') }}">Descargar PDF</a>
      <a class="btn btn--ghost" href="{{ url_for('reportes.index', tipo=tipo, preset='rango', desde=desde, hasta=hasta, formato='xlsx') }}">Descargar XLSX</a>
    </div>
  </div>

  <div class="card">
    <h2 class="card__title">{{ titulo }} <span class="muted" style="font-weight:400">({{ desde }} — {{ hasta }})</span></h2>
    <div style="overflow-x:auto;">
    <table class="table">
      <thead><tr>{% for h in headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
      <tbody>
        {% for row in rows %}<tr>{% for c in row %}<td>{{ c }}</td>{% endfor %}</tr>
        {% else %}<tr><td colspan="{{ headers|length }}" class="muted">Sin datos en el rango.</td></tr>{% endfor %}
        {% if rows %}<tr style="font-weight:700;">{% for c in total_row %}<td>{{ c }}</td>{% endfor %}</tr>{% endif %}
      </tbody>
    </table>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 6: Register the blueprint**

En `web/app/__init__.py`, importar y registrar junto a los demás:

```python
    from app.auth.routes import bp as auth_bp
    from app.dashboard.routes import bp as dashboard_bp
    from app.reportes.routes import bp as reportes_bp
    from app.usuarios.routes import bp as usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reportes_bp)
    app.register_blueprint(usuarios_bp)
```

- [ ] **Step 7: Add "Reportes" to the sidebar**

En `web/app/templates/base.html`, dentro de `<nav class="sidebar__nav">`, después del enlace de "Usuarios y Roles", añadir:

```html
      <a class="sidebar__link {{ 'active' if request.endpoint and request.endpoint.startswith('reportes.') }}" href="{{ url_for('reportes.index') }}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 2h9l5 5v15H6z"/><path d="M14 2v6h6M9 13h6M9 17h6"/></svg>
        Reportes
      </a>
```

- [ ] **Step 8: Run tests to verify they pass**

Run: `docker compose exec web pytest tests/test_reportes.py -v`
Expected: PASS (5 tests).

- [ ] **Step 9: Commit (local)**

```bash
git add web/app/services/api_client.py web/app/reportes/ \
        web/app/templates/reportes/index.html web/app/__init__.py \
        web/app/templates/base.html web/tests/test_reportes.py
git commit -m "feat(web): página /reportes con vista previa (ventas/gastos)"
```

---

## Task 4: Web — export PDF (WeasyPrint) + XLSX (openpyxl)

**Files:**
- Create: `web/app/services/export.py`
- Create: `web/app/templates/reportes/print.html`
- Modify: `web/app/reportes/routes.py`
- Test: `web/tests/test_reportes.py`

**Interfaces:**
- Consumes: `_reporte(tipo, filas)` (Task 3), `to_xlsx`/`to_pdf` (este task).
- Produces:
  - `export.to_xlsx(sheet_title, headers, rows, total_row) -> bytes`.
  - `export.to_pdf(html_string) -> bytes`.
  - `/reportes?formato=pdf|xlsx` devuelve el archivo como adjunto.

- [ ] **Step 1: Write the failing test**

Añadir a `web/tests/test_reportes.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_reportes.py -k export -v`
Expected: FAIL — hoy `formato` se ignora y devuelve HTML (mimetype `text/html`).

- [ ] **Step 3: Create the export helpers**

Crear `web/app/services/export.py`:

```python
from io import BytesIO

from openpyxl import Workbook
from weasyprint import HTML


def to_xlsx(sheet_title, headers, rows, total_row):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]  # límite de Excel
    ws.append(headers)
    for row in rows:
        ws.append(row)
    if rows:
        ws.append(total_row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(html_string):
    return HTML(string=html_string).write_pdf()
```

- [ ] **Step 4: Create the print template**

Crear `web/app/templates/reportes/print.html`:

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <style>
    body { font-family: Georgia, serif; color: #2c1e16; margin: 24px; }
    h1 { font-size: 18px; margin: 0 0 2px; }
    .sub { color: #6b5647; font-size: 12px; margin: 0 0 16px; }
    table { width: 100%; border-collapse: collapse; font-size: 11px; }
    th, td { border-bottom: 1px solid #ccc; padding: 6px 8px; text-align: left; }
    th { background: #f0ebe4; }
    tr.total td { font-weight: bold; border-top: 2px solid #999; }
  </style>
</head>
<body>
  <h1>{{ titulo }}</h1>
  <p class="sub">Rango: {{ desde }} — {{ hasta }}</p>
  <table>
    <thead><tr>{% for h in headers %}<th>{{ h }}</th>{% endfor %}</tr></thead>
    <tbody>
      {% for row in rows %}<tr>{% for c in row %}<td>{{ c }}</td>{% endfor %}</tr>
      {% else %}<tr><td colspan="{{ headers|length }}">Sin datos en el rango.</td></tr>{% endfor %}
      {% if rows %}<tr class="total">{% for c in total_row %}<td>{{ c }}</td>{% endfor %}</tr>{% endif %}
    </tbody>
  </table>
</body>
</html>
```

- [ ] **Step 5: Wire export into the route**

En `web/app/reportes/routes.py`, actualizar los imports y añadir el manejo de `formato` dentro de `index()`. Import nuevo:

```python
from flask import Blueprint, Response, render_template, request
from flask_login import login_required

from app.dashboard.routes import rango_preset
from app.services import api_client, api_gateway, export
```

Reemplazar el `return render_template(...)` final de `index()` por:

```python
    formato = request.args.get("formato")
    if formato in ("xlsx", "pdf"):
        base = f"reporte-{tipo}-{desde}_{hasta}"
        if formato == "xlsx":
            data = export.to_xlsx(titulo, headers, rows, total_row)
            ctype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            fname = f"{base}.xlsx"
        else:
            html = render_template(
                "reportes/print.html",
                titulo=titulo, headers=headers, rows=rows, total_row=total_row,
                desde=desde, hasta=hasta,
            )
            data = export.to_pdf(html)
            ctype = "application/pdf"
            fname = f"{base}.pdf"
        return Response(
            data,
            mimetype=ctype,
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    return render_template(
        "reportes/index.html",
        tipo=tipo, titulo=titulo, headers=headers, rows=rows, total_row=total_row,
        preset=preset, desde=desde, hasta=hasta,
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose exec web pytest tests/test_reportes.py -v`
Expected: PASS (7 tests — preview + export xlsx/pdf).

- [ ] **Step 7: Full web suite + smoke**

Run: `docker compose exec web pytest`
Expected: PASS (todos).

Smoke manual: `docker compose restart web`; con sesión admin en `localhost:5000/reportes`, cambiar tipo Ventas/Gastos y periodo, ver la vista previa, y descargar PDF y XLSX (que abran correctamente).

- [ ] **Step 8: Commit (local)**

```bash
git add web/app/services/export.py web/app/templates/reportes/print.html \
        web/app/reportes/routes.py web/tests/test_reportes.py
git commit -m "feat(web): export de reportes a PDF (WeasyPrint) y XLSX (openpyxl)"
```

---

## Definition of Done (Slice B)

- API: `GET /reportes/{ventas,gastos}` (detalle, solo Admin, filtro de fechas).
- Web: página `/reportes` con selector de tipo, periodo (pills + rango), vista previa con totales, y descarga PDF/XLSX. Ítem "Reportes" en el sidebar.
- Export: XLSX (openpyxl) y PDF (WeasyPrint, plantilla Jinja), con `Content-Disposition: attachment`.
- Dockerfile del web con libs nativas; imagen reconstruida localmente.
- Suites backend y web en verde. Sin migraciones. Todo en `feature/sprint6-backlog` (commits locales, sin push/PR).
- Fuera de alcance: tipos Productos/Inventario/Pedidos, filtros categoría/usuario/método/agrupar-por, gráfica en el reporte.
