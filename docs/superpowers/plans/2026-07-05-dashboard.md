# Sprint 6 · Slice A — Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir endpoints de agregación de reportes en la API y una pantalla `/dashboard` en el panel web con KPIs y gráficas (Chart.js) filtrables por periodo.

**Architecture:** Opción A — la API (FastAPI) agrega con SQL (`GROUP BY`/`SUM`) y expone `GET /reportes/*` (solo Admin). El panel web (Flask, cliente delgado) consume esos JSON, pinta tarjetas de KPI y dos gráficas con Chart.js vendorizado localmente. Sin cambios de BD/migraciones.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Flask + Jinja2 + Chart.js (web), pytest (ambos).

## Global Constraints

- **Autorización:** todos los `GET /reportes/*` usan `Depends(deps.require_admin)` → 403 para no-admin. Las rutas web usan `@login_required`.
- **Prefijo API:** todo cuelga de `/api/v1` (el router raíz ya aplica el prefijo). El router de reportes usa `prefix="/reportes"`.
- **Fechas:** query params `desde` y `hasta` tipo `date` (`YYYY-MM-DD`), ambos inclusive. Si faltan, default = `date.today()` para ambos. El filtro compara `func.date(columna)` BETWEEN desde AND hasta.
- **Solo ventas Completadas:** los agregados de ventas filtran `Venta.estado_venta == "Completada"`.
- **Utilidad estimada:** `total_vendido - total_gastos - total_compras` (documentada como estimada; no resta costo de venta por receta).
- **Sin migraciones nuevas:** este slice solo lee tablas existentes (`ventas`, `pedidos`, `detalle_pedido`, `productos`, `gastos`, `compras`).
- **Estilo money:** los importes se serializan como `Decimal` (Pydantic los emite como número JSON), igual que en `GastoOut`/`VentaOut`.
- **Comandos de test:** backend `docker compose exec api pytest`; web `docker compose exec web pytest` (o `cd web && pytest`).

---

## File Structure

**Backend (crear):**
- `backend/app/schemas/reporte.py` — schemas `ResumenOut`, `VentaPorDiaOut`, `TopProductoOut`.
- `backend/app/services/reporte_service.py` — funciones de agregación + helper de rango de fechas.
- `backend/app/api/v1/reportes.py` — router con 3 endpoints GET.
- `backend/tests/test_reportes_api.py` — tests de los 3 endpoints.

**Backend (modificar):**
- `backend/app/api/v1/router.py` — importar y registrar `reportes.router`.

**Web (crear):**
- `web/app/dashboard/__init__.py` — paquete vacío.
- `web/app/dashboard/routes.py` — blueprint `dashboard` con ruta `/dashboard` + helper de presets de fecha.
- `web/app/templates/dashboard/index.html` — KPIs + `<canvas>` de las gráficas + JSON embebido + `<script>` Chart.js.
- `web/app/static/vendor/chart.umd.min.js` — Chart.js vendorizado.
- `web/tests/test_dashboard.py` — tests de la ruta.

**Web (modificar):**
- `web/app/services/api_client.py` — añadir `get_reporte_resumen`, `get_ventas_por_dia`, `get_top_productos`.
- `web/app/__init__.py` — registrar blueprint `dashboard`, cambiar `index()` para redirigir a `dashboard.index`.
- `web/app/templates/base.html` — enlaces "Dashboard" y "Reportes" en el `nav`.

---

## Task 1: API — schemas + endpoint `GET /reportes/resumen` (KPIs)

**Files:**
- Create: `backend/app/schemas/reporte.py`
- Create: `backend/app/services/reporte_service.py`
- Create: `backend/app/api/v1/reportes.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_reportes_api.py`

**Interfaces:**
- Produces:
  - `reporte_service.rango(desde: date | None, hasta: date | None) -> tuple[date, date]` (default hoy/hoy).
  - `reporte_service.resumen(db: Session, desde: date, hasta: date) -> dict` con claves
    `total_vendido, num_ventas, ticket_promedio, total_gastos, total_compras, utilidad_estimada` (todas `Decimal`/`int`).
  - Endpoint `GET /api/v1/reportes/resumen?desde&hasta` → `ResumenOut`.

- [ ] **Step 1: Write the failing test**

Crear `backend/tests/test_reportes_api.py` con un helper local para sembrar una venta y los primeros casos:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec api pytest tests/test_reportes_api.py -v`
Expected: FAIL — 404 en `/api/v1/reportes/resumen` (router aún no existe).

- [ ] **Step 3: Write the schemas**

Crear `backend/app/schemas/reporte.py`:

```python
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ResumenOut(BaseModel):
    total_vendido: Decimal
    num_ventas: int
    ticket_promedio: Decimal
    total_gastos: Decimal
    total_compras: Decimal
    utilidad_estimada: Decimal


class VentaPorDiaOut(BaseModel):
    fecha: date
    total: Decimal
    num_ventas: int


class TopProductoOut(BaseModel):
    id_producto: int
    nombre: str
    cantidad: int
    importe: Decimal
```

- [ ] **Step 4: Write the service**

Crear `backend/app/services/reporte_service.py`:

```python
from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Compra, Gasto, Venta

_CERO = Decimal("0.00")


def rango(desde: date | None, hasta: date | None) -> tuple[date, date]:
    hoy = date.today()
    return (desde or hoy, hasta or hoy)


def _suma(db: Session, columna, fecha_col, desde: date, hasta: date, *filtros):
    q = db.query(func.coalesce(func.sum(columna), 0)).filter(
        func.date(fecha_col) >= desde, func.date(fecha_col) <= hasta
    )
    for f in filtros:
        q = q.filter(f)
    return Decimal(str(q.scalar() or 0))


def resumen(db: Session, desde: date, hasta: date) -> dict:
    completada = Venta.estado_venta == "Completada"
    total_vendido = _suma(
        db, Venta.total, Venta.fecha_venta, desde, hasta, completada
    )
    num_ventas = (
        db.query(func.count(Venta.id_venta))
        .filter(
            func.date(Venta.fecha_venta) >= desde,
            func.date(Venta.fecha_venta) <= hasta,
            completada,
        )
        .scalar()
    )
    total_gastos = _suma(db, Gasto.monto, Gasto.fecha_gasto, desde, hasta)
    total_compras = _suma(db, Compra.total, Compra.fecha_compra, desde, hasta)
    ticket = (
        (total_vendido / num_ventas).quantize(Decimal("0.01"))
        if num_ventas
        else _CERO
    )
    return {
        "total_vendido": total_vendido,
        "num_ventas": num_ventas,
        "ticket_promedio": ticket,
        "total_gastos": total_gastos,
        "total_compras": total_compras,
        "utilidad_estimada": total_vendido - total_gastos - total_compras,
    }
```

- [ ] **Step 5: Write the router**

Crear `backend/app/api/v1/reportes.py`:

```python
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.reporte import ResumenOut
from app.services import reporte_service

router = APIRouter(prefix="/reportes", tags=["reportes"])


@router.get("/resumen", response_model=ResumenOut)
def resumen(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.resumen(db, d, h)
```

- [ ] **Step 6: Register the router**

En `backend/app/api/v1/router.py`, añadir `reportes` al import y una línea `api_router.include_router(reportes.router)`:

```python
from app.api.v1 import (
    auth,
    categorias,
    compras,
    estados,
    gastos,
    insumos,
    mesas,
    metodos_pago,
    pedidos,
    productos,
    proveedores,
    recetas,
    reportes,
    roles,
    unidades,
    usuarios,
    ventas,
)
```

y (tras `compras.router`):

```python
api_router.include_router(reportes.router)
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker compose exec api pytest tests/test_reportes_api.py -v`
Expected: PASS (5 tests).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/reporte.py backend/app/services/reporte_service.py \
        backend/app/api/v1/reportes.py backend/app/api/v1/router.py \
        backend/tests/test_reportes_api.py
git commit -m "feat(api): reportes/resumen (KPIs del periodo)"
```

---

## Task 2: API — endpoint `GET /reportes/ventas-por-dia`

**Files:**
- Modify: `backend/app/services/reporte_service.py`
- Modify: `backend/app/api/v1/reportes.py`
- Test: `backend/tests/test_reportes_api.py`

**Interfaces:**
- Consumes: `_cobrar`, `_fechar_venta` (helpers ya en el test), `reporte_service.rango`.
- Produces:
  - `reporte_service.ventas_por_dia(db, desde, hasta) -> list[dict]` con `{fecha: date, total: Decimal, num_ventas: int}`, ordenado por fecha asc.
  - Endpoint `GET /api/v1/reportes/ventas-por-dia?desde&hasta` → `list[VentaPorDiaOut]`.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_reportes_api.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec api pytest tests/test_reportes_api.py::test_ventas_por_dia_agrupa_por_fecha -v`
Expected: FAIL — 404 (endpoint no existe).

- [ ] **Step 3: Add the service function**

Añadir a `backend/app/services/reporte_service.py`:

```python
def ventas_por_dia(db: Session, desde: date, hasta: date) -> list[dict]:
    dia = func.date(Venta.fecha_venta)
    filas = (
        db.query(
            dia.label("fecha"),
            func.coalesce(func.sum(Venta.total), 0).label("total"),
            func.count(Venta.id_venta).label("num_ventas"),
        )
        .filter(
            dia >= desde,
            dia <= hasta,
            Venta.estado_venta == "Completada",
        )
        .group_by(dia)
        .order_by(dia)
        .all()
    )
    return [
        {
            "fecha": f.fecha,
            "total": Decimal(str(f.total)),
            "num_ventas": f.num_ventas,
        }
        for f in filas
    ]
```

- [ ] **Step 4: Add the endpoint**

En `backend/app/api/v1/reportes.py` añadir el import y el endpoint:

```python
from app.schemas.reporte import ResumenOut, VentaPorDiaOut
```

```python
@router.get("/ventas-por-dia", response_model=list[VentaPorDiaOut])
def ventas_por_dia(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.ventas_por_dia(db, d, h)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose exec api pytest tests/test_reportes_api.py -v`
Expected: PASS (todos, incluidos los nuevos).

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/reporte_service.py backend/app/api/v1/reportes.py \
        backend/tests/test_reportes_api.py
git commit -m "feat(api): reportes/ventas-por-dia (serie temporal)"
```

---

## Task 3: API — endpoint `GET /reportes/top-productos`

**Files:**
- Modify: `backend/app/services/reporte_service.py`
- Modify: `backend/app/api/v1/reportes.py`
- Test: `backend/tests/test_reportes_api.py`

**Interfaces:**
- Consumes: `_cobrar`, `reporte_service.rango`.
- Produces:
  - `reporte_service.top_productos(db, desde, hasta, limite: int = 10) -> list[dict]` con
    `{id_producto: int, nombre: str, cantidad: int, importe: Decimal}`, ordenado por cantidad desc.
  - Endpoint `GET /api/v1/reportes/top-productos?desde&hasta&limite=10` → `list[TopProductoOut]`.

- [ ] **Step 1: Write the failing test**

Añadir a `backend/tests/test_reportes_api.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec api pytest tests/test_reportes_api.py::test_top_productos_ordena_por_cantidad -v`
Expected: FAIL — 404 (endpoint no existe).

- [ ] **Step 3: Add the service function**

Añadir a `backend/app/services/reporte_service.py` (añadir `DetallePedido`, `Pedido`, `Producto` al import de `app.models`):

```python
from app.models import (
    Compra,
    DetallePedido,
    Gasto,
    Pedido,
    Producto,
    Venta,
)
```

```python
def top_productos(
    db: Session, desde: date, hasta: date, limite: int = 10
) -> list[dict]:
    dia = func.date(Venta.fecha_venta)
    filas = (
        db.query(
            Producto.id_producto.label("id_producto"),
            Producto.nombre_producto.label("nombre"),
            func.sum(DetallePedido.cantidad).label("cantidad"),
            func.sum(DetallePedido.subtotal).label("importe"),
        )
        .join(Pedido, Pedido.id_pedido == Venta.id_pedido)
        .join(DetallePedido, DetallePedido.id_pedido == Pedido.id_pedido)
        .join(Producto, Producto.id_producto == DetallePedido.id_producto)
        .filter(
            dia >= desde,
            dia <= hasta,
            Venta.estado_venta == "Completada",
        )
        .group_by(Producto.id_producto, Producto.nombre_producto)
        .order_by(func.sum(DetallePedido.cantidad).desc())
        .limit(limite)
        .all()
    )
    return [
        {
            "id_producto": f.id_producto,
            "nombre": f.nombre,
            "cantidad": int(f.cantidad),
            "importe": Decimal(str(f.importe)),
        }
        for f in filas
    ]
```

- [ ] **Step 4: Add the endpoint**

En `backend/app/api/v1/reportes.py` actualizar el import y añadir el endpoint:

```python
from app.schemas.reporte import ResumenOut, TopProductoOut, VentaPorDiaOut
```

```python
@router.get("/top-productos", response_model=list[TopProductoOut])
def top_productos(
    desde: date | None = None,
    hasta: date | None = None,
    limite: int = 10,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.top_productos(db, d, h, limite)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `docker compose exec api pytest tests/test_reportes_api.py -v`
Expected: PASS (todos).

- [ ] **Step 6: Full backend suite (no regresiones)**

Run: `docker compose exec api pytest`
Expected: PASS (144 previos + los nuevos de reportes).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/reporte_service.py backend/app/api/v1/reportes.py \
        backend/tests/test_reportes_api.py
git commit -m "feat(api): reportes/top-productos (ranking por cantidad)"
```

---

## Task 4: Web — cliente API de reportes + ruta `/dashboard` con KPIs

**Files:**
- Modify: `web/app/services/api_client.py`
- Create: `web/app/dashboard/__init__.py`
- Create: `web/app/dashboard/routes.py`
- Create: `web/app/templates/dashboard/index.html`
- Modify: `web/app/__init__.py`
- Modify: `web/app/templates/base.html`
- Test: `web/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `api_gateway.call`, patrón de `usuarios/routes.py`.
- Produces:
  - `api_client.get_reporte_resumen(access, desde, hasta) -> dict`
  - `api_client.get_ventas_por_dia(access, desde, hasta) -> list[dict]`
  - `api_client.get_top_productos(access, desde, hasta, limite=10) -> list[dict]`
  - Blueprint `dashboard` con endpoint `dashboard.index` en `/dashboard`.
  - `dashboard.routes.rango_preset(preset, desde, hasta) -> tuple[str, str]` (calcula `desde`/`hasta` ISO).

- [ ] **Step 1: Write the failing test**

Crear `web/tests/test_dashboard.py`:

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_dashboard.py -v`
Expected: FAIL — 404 en `/dashboard` (blueprint no registrado).

- [ ] **Step 3: Add API client functions**

Añadir a `web/app/services/api_client.py` (al final):

```python
def get_reporte_resumen(access, desde=None, hasta=None):
    r = requests.get(
        f"{_base()}/reportes/resumen",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta},
        timeout=TIMEOUT,
    )
    return _check(r)


def get_ventas_por_dia(access, desde=None, hasta=None):
    r = requests.get(
        f"{_base()}/reportes/ventas-por-dia",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta},
        timeout=TIMEOUT,
    )
    return _check(r)


def get_top_productos(access, desde=None, hasta=None, limite=10):
    r = requests.get(
        f"{_base()}/reportes/top-productos",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta, "limite": limite},
        timeout=TIMEOUT,
    )
    return _check(r)
```

- [ ] **Step 4: Create the blueprint with date presets**

Crear `web/app/dashboard/__init__.py` vacío, y `web/app/dashboard/routes.py`:

```python
from datetime import date, timedelta

from flask import Blueprint, render_template, request
from flask_login import login_required

from app.services import api_client, api_gateway

bp = Blueprint("dashboard", __name__)


def rango_preset(preset, desde, hasta):
    """Devuelve (desde, hasta) en ISO según el preset o el rango explícito."""
    hoy = date.today()
    if preset == "7dias":
        return (hoy - timedelta(days=6)).isoformat(), hoy.isoformat()
    if preset == "mes":
        return hoy.replace(day=1).isoformat(), hoy.isoformat()
    if preset == "rango" and desde and hasta:
        return desde, hasta
    return hoy.isoformat(), hoy.isoformat()  # "hoy" (default)


@bp.route("/dashboard")
@login_required
def index():
    preset = request.args.get("preset", "hoy")
    desde, hasta = rango_preset(
        preset, request.args.get("desde"), request.args.get("hasta")
    )
    resumen = api_gateway.call(api_client.get_reporte_resumen, desde, hasta)
    serie = api_gateway.call(api_client.get_ventas_por_dia, desde, hasta)
    top = api_gateway.call(api_client.get_top_productos, desde, hasta)
    return render_template(
        "dashboard/index.html",
        resumen=resumen, serie=serie, top=top,
        preset=preset, desde=desde, hasta=hasta,
    )
```

- [ ] **Step 5: Create the template (KPIs, gráficas se añaden en Task 5)**

Crear `web/app/templates/dashboard/index.html`:

```html
{% extends "base.html" %}
{% block title %}Dashboard{% endblock %}
{% block content %}
<div class="header-row">
  <h1>Dashboard</h1>
</div>

<form method="get" class="filtros">
  <label>Periodo:
    <select name="preset" onchange="this.form.submit()">
      <option value="hoy" {{ 'selected' if preset == 'hoy' }}>Hoy</option>
      <option value="7dias" {{ 'selected' if preset == '7dias' }}>Últimos 7 días</option>
      <option value="mes" {{ 'selected' if preset == 'mes' }}>Este mes</option>
      <option value="rango" {{ 'selected' if preset == 'rango' }}>Rango…</option>
    </select>
  </label>
  <input type="date" name="desde" value="{{ desde }}">
  <input type="date" name="hasta" value="{{ hasta }}">
  <button type="submit">Aplicar</button>
</form>

<section class="kpis">
  <div class="kpi"><span class="kpi__label">Total vendido</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.total_vendido|float) }}</span></div>
  <div class="kpi"><span class="kpi__label"># Ventas</span>
    <span class="kpi__value">{{ resumen.num_ventas }}</span></div>
  <div class="kpi"><span class="kpi__label">Ticket promedio</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.ticket_promedio|float) }}</span></div>
  <div class="kpi"><span class="kpi__label">Gastos</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.total_gastos|float) }}</span></div>
  <div class="kpi"><span class="kpi__label">Compras</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.total_compras|float) }}</span></div>
  <div class="kpi kpi--accent"><span class="kpi__label">Utilidad estimada</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.utilidad_estimada|float) }}</span></div>
</section>
{% endblock %}
```

- [ ] **Step 6: Register blueprint and change index redirect**

En `web/app/__init__.py`:
- Importar y registrar el blueprint junto a los demás:

```python
    from app.auth.routes import bp as auth_bp
    from app.dashboard.routes import bp as dashboard_bp
    from app.usuarios.routes import bp as usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(usuarios_bp)
```

- Cambiar `index()`:

```python
    @app.route("/")
    def index():
        return redirect(url_for("dashboard.index"))
```

- [ ] **Step 7: Add nav links**

En `web/app/templates/base.html`, dentro de `<div class="nav__links">`, antes del enlace de Usuarios:

```html
      <a href="{{ url_for('dashboard.index') }}">Dashboard</a>
      <a href="{{ url_for('usuarios.listar') }}">Usuarios</a>
```

(Nota: el enlace "Reportes" se añade en el Slice B.)

- [ ] **Step 8: Run tests to verify they pass**

Run: `docker compose exec web pytest tests/test_dashboard.py -v`
Expected: PASS (4 tests).

- [ ] **Step 9: Commit**

```bash
git add web/app/services/api_client.py web/app/dashboard/ \
        web/app/templates/dashboard/index.html web/app/__init__.py \
        web/app/templates/base.html web/tests/test_dashboard.py
git commit -m "feat(web): dashboard con KPIs del periodo (Slice A)"
```

---

## Task 5: Web — gráficas Chart.js (ventas/día y top productos)

**Files:**
- Create: `web/app/static/vendor/chart.umd.min.js`
- Modify: `web/app/templates/dashboard/index.html`
- Modify: `web/app/static/css/app.css`
- Test: `web/tests/test_dashboard.py`

**Interfaces:**
- Consumes: variables `serie` y `top` ya pasadas al template en Task 4.
- Produces: dos `<canvas>` (`#chart-ventas`, `#chart-top`) dibujados con Chart.js a partir de JSON embebido con `|tojson`.

- [ ] **Step 1: Write the failing test**

Añadir a `web/tests/test_dashboard.py`:

```python
def test_dashboard_incluye_graficas(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    r = client.get("/dashboard")
    cuerpo = r.get_data(as_text=True)
    assert 'id="chart-ventas"' in cuerpo
    assert 'id="chart-top"' in cuerpo
    assert "chart.umd.min.js" in cuerpo
    assert "Café" in cuerpo          # dato del top embebido en el JSON
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_dashboard.py::test_dashboard_incluye_graficas -v`
Expected: FAIL — el template aún no tiene los `<canvas>` ni el script.

- [ ] **Step 3: Vendorizar Chart.js**

Descargar Chart.js UMD minificado a `web/app/static/vendor/chart.umd.min.js`:

```bash
mkdir -p web/app/static/vendor
curl -fsSL https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js \
  -o web/app/static/vendor/chart.umd.min.js
test -s web/app/static/vendor/chart.umd.min.js && echo OK
```

Si el entorno no tiene red, obtener el archivo `chart.umd.min.js` de Chart.js v4.4.1 por otro medio y colocarlo en esa ruta. Debe pesar > 100 KB (`test -s` confirma que no está vacío).

- [ ] **Step 4: Add canvases + chart script to template**

Añadir al final del `{% block content %}` de `web/app/templates/dashboard/index.html`, **antes** de `{% endblock %}`:

```html
<section class="graficas">
  <div class="grafica"><h2>Ventas por día</h2><canvas id="chart-ventas"></canvas></div>
  <div class="grafica"><h2>Productos más vendidos</h2><canvas id="chart-top"></canvas></div>
</section>

<script id="serie-data" type="application/json">{{ serie|tojson }}</script>
<script id="top-data" type="application/json">{{ top|tojson }}</script>
<script src="{{ url_for('static', filename='vendor/chart.umd.min.js') }}"></script>
<script>
  const serie = JSON.parse(document.getElementById("serie-data").textContent);
  const top = JSON.parse(document.getElementById("top-data").textContent);
  new Chart(document.getElementById("chart-ventas"), {
    type: "line",
    data: {
      labels: serie.map(p => p.fecha),
      datasets: [{ label: "Ventas ($)", data: serie.map(p => Number(p.total)),
                   borderColor: "#2563eb", tension: 0.2 }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
  new Chart(document.getElementById("chart-top"), {
    type: "bar",
    data: {
      labels: top.map(p => p.nombre),
      datasets: [{ label: "Cantidad", data: top.map(p => Number(p.cantidad)),
                   backgroundColor: "#16a34a" }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
</script>
```

- [ ] **Step 5: Add minimal styles**

Añadir a `web/app/static/css/app.css`:

```css
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 16px 0; }
.kpi { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; display: flex; flex-direction: column; }
.kpi--accent { background: #ecfdf5; border-color: #a7f3d0; }
.kpi__label { font-size: 12px; color: #64748b; }
.kpi__value { font-size: 22px; font-weight: 700; }
.filtros { display: flex; gap: 8px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }
.graficas { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px; margin-top: 20px; }
.grafica { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose exec web pytest tests/test_dashboard.py -v`
Expected: PASS (5 tests).

- [ ] **Step 7: Full web suite (no regresiones)**

Run: `docker compose exec web pytest`
Expected: PASS (13 previos + los nuevos de dashboard).

- [ ] **Step 8: Manual smoke check**

Con `docker compose up -d` y sesión de admin en `localhost:5000/dashboard`: se ven las 6 tarjetas de KPI, el selector de periodo cambia los datos, y ambas gráficas renderizan. Verifica también un rango sin datos (no debe romper: series vacías → gráficas vacías).

- [ ] **Step 9: Commit**

```bash
git add web/app/static/vendor/chart.umd.min.js \
        web/app/templates/dashboard/index.html web/app/static/css/app.css \
        web/tests/test_dashboard.py
git commit -m "feat(web): gráficas Chart.js en el dashboard (Slice A)"
```

---

## Definition of Done (Slice A)

- API: `GET /reportes/{resumen,ventas-por-dia,top-productos}` funcionando, solo Admin (403 no-admin, 401 sin token), filtrables por `desde`/`hasta`.
- Web: `/dashboard` con 6 KPIs, selector de periodo (Hoy / 7 días / Este mes / Rango) y dos gráficas Chart.js. `/` redirige a `/dashboard`. Nav con enlace "Dashboard".
- Tests: suite backend y web en verde (`docker compose exec api pytest` y `docker compose exec web pytest`).
- Sin migraciones nuevas. Chart.js vendorizado (sin CDN en runtime).
- Fuera de este slice: reportes filtrables + export PDF/XLSX (Slice B), enlace "Reportes" en el nav.
