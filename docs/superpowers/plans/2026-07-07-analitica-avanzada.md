# Analítica avanzada (widgets de Estadísticas) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a Estadísticas KPIs con variación vs periodo anterior (color por beneficio de negocio), dona de productos, tendencia de pedidos diarios y nivel de inventario.

**Architecture:** Opción A — dos endpoints nuevos (`comparativo`, `inventario-niveles`) + reuso de `top-productos`/`ventas-por-dia`. La regla de color del delta se resuelve en la **ruta Flask** (no en Jinja). Cliente delgado, sin migraciones.

**Tech Stack:** FastAPI + SQLAlchemy (backend); Flask + Jinja2 + Chart.js (web); pytest.

## Global Constraints

- **Trabajo local:** commits locales en `feature/sprint6-backlog`. NO push, NO PRs.
- **Sin migraciones.** Solo lectura.
- **Autorización:** `GET /reportes/*` con `Depends(deps.require_admin)` (403/401). Web `@login_required`.
- **Periodo anterior:** `n = (hasta - desde).days + 1`; `anterior = [desde - n días, desde - 1 día]`.
- **delta** = `round((actual - anterior)/anterior * 100, 1)` (float); `null` si `anterior == 0`.
- **`comparativo.actual`/`.anterior`** = el dict completo de `reporte_service.resumen` (6 métricas); `deltas` cubre las 4: `total_vendido, total_gastos, utilidad_estimada, num_ventas`.
- **nivel_pct** = `min(100, round(stock_actual/(2*stock_minimo)*100))` si `stock_minimo>0`; si no, `100` cuando `stock_actual>0` si no `0`. `bajo_minimo = stock_actual < stock_minimo`.
- **Regla de color (por polaridad `up_is_good`):** Total vendido/Utilidad/# Ventas → `True`; **Gastos → `False`**. `color="up"` (verde) si `(delta>0)==up_is_good`; `"down"` (rojo) si no; `"neutral"` si `delta` es `null` o `0`. Flecha `▲` si `delta>0`, `▼` si `delta<0`.
- **Tests:** backend `docker compose exec api pytest`; web `docker compose exec web pytest`.
- Money como `Decimal` en schemas; `delta` como `float | None`.

---

## File Structure

**Backend (modificar):**
- `backend/app/schemas/reporte.py` — `+ DeltasOut`, `+ ComparativoOut`, `+ InventarioNivelOut`.
- `backend/app/services/reporte_service.py` — `+ comparativo`, `+ inventario_niveles` (import `Insumo`).
- `backend/app/api/v1/reportes.py` — `+ GET /reportes/comparativo`, `+ GET /reportes/inventario-niveles`.
- `backend/tests/test_reportes_api.py` — tests.

**Web (modificar):**
- `web/app/services/api_client.py` — `+ get_comparativo`, `+ get_inventario_niveles`.
- `web/app/dashboard/routes.py` — usar `comparativo`, construir `kpis` (con color), fetch `inventario-niveles`.
- `web/app/templates/dashboard/index.html` — KPIs con delta; dona; línea de tendencia; barras de inventario.
- `web/app/static/css/app.css` — clases de delta y barras de inventario.
- `web/tests/test_dashboard.py` — actualizar stubs (comparativo) y añadir tests.

---

## Task 1: API — `GET /reportes/comparativo`

**Files:**
- Modify: `backend/app/schemas/reporte.py`
- Modify: `backend/app/services/reporte_service.py`
- Modify: `backend/app/api/v1/reportes.py`
- Test: `backend/tests/test_reportes_api.py`

**Interfaces:**
- Consumes: `reporte_service.rango`, `reporte_service.resumen`; test helpers `_cobrar` y `_fechar_venta` (ya en el test desde Slice A/B: `_fechar_venta(db, id_venta, cuando: datetime)` reescribe `fecha_venta`).
- Produces:
  - `reporte_service.comparativo(db, desde, hasta) -> dict` con `{actual: dict, anterior: dict, deltas: {total_vendido, total_gastos, utilidad_estimada, num_ventas}}` (deltas float|None).
  - `GET /api/v1/reportes/comparativo?desde&hasta` → `ComparativoOut`.

- [ ] **Step 1: Write the failing tests**

Añadir a `backend/tests/test_reportes_api.py` (los imports `date, datetime, timezone, Decimal` ya están en el archivo):

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec api pytest tests/test_reportes_api.py -k comparativo -v`
Expected: FAIL — 404 (endpoint no existe).

- [ ] **Step 3: Add the schemas**

En `backend/app/schemas/reporte.py`, añadir al final:

```python
class DeltasOut(BaseModel):
    total_vendido: float | None
    total_gastos: float | None
    utilidad_estimada: float | None
    num_ventas: float | None


class ComparativoOut(BaseModel):
    actual: ResumenOut
    anterior: ResumenOut
    deltas: DeltasOut
```

- [ ] **Step 4: Add the service function**

En `backend/app/services/reporte_service.py`, añadir `from datetime import timedelta` al import de datetime (cambiar la primera línea a `from datetime import date, timedelta`) y añadir:

```python
def comparativo(db: Session, desde: date, hasta: date) -> dict:
    n = (hasta - desde).days + 1
    ant_hasta = desde - timedelta(days=1)
    ant_desde = desde - timedelta(days=n)
    actual = resumen(db, desde, hasta)
    anterior = resumen(db, ant_desde, ant_hasta)

    def _delta(a, b) -> float | None:
        b = Decimal(str(b))
        if b == 0:
            return None
        return float(round((Decimal(str(a)) - b) / b * 100, 1))

    claves = ("total_vendido", "total_gastos", "utilidad_estimada", "num_ventas")
    deltas = {k: _delta(actual[k], anterior[k]) for k in claves}
    return {"actual": actual, "anterior": anterior, "deltas": deltas}
```

- [ ] **Step 5: Add the endpoint**

En `backend/app/api/v1/reportes.py`, actualizar el import de schemas para incluir `ComparativoOut` y añadir:

```python
@router.get("/comparativo", response_model=ComparativoOut)
def comparativo(
    desde: date | None = None,
    hasta: date | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    d, h = reporte_service.rango(desde, hasta)
    return reporte_service.comparativo(db, d, h)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `docker compose exec api pytest tests/test_reportes_api.py -k comparativo -v`
Expected: PASS (3 tests).

- [ ] **Step 7: Commit (local)**

```bash
git add backend/app/schemas/reporte.py backend/app/services/reporte_service.py \
        backend/app/api/v1/reportes.py backend/tests/test_reportes_api.py
git commit -m "feat(api): reportes/comparativo (KPIs vs periodo anterior)"
```

---

## Task 2: API — `GET /reportes/inventario-niveles`

**Files:**
- Modify: `backend/app/schemas/reporte.py`
- Modify: `backend/app/services/reporte_service.py`
- Modify: `backend/app/api/v1/reportes.py`
- Test: `backend/tests/test_reportes_api.py`

**Interfaces:**
- Produces:
  - `reporte_service.inventario_niveles(db) -> list[dict]` con `{nombre, unidad, stock_actual, stock_minimo, nivel_pct: int, bajo_minimo: bool}`, ordenado por `nivel_pct` asc.
  - `GET /api/v1/reportes/inventario-niveles` → `list[InventarioNivelOut]`.

- [ ] **Step 1: Write the failing tests**

Añadir a `backend/tests/test_reportes_api.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec api pytest tests/test_reportes_api.py -k inventario -v`
Expected: FAIL — 404.

- [ ] **Step 3: Add the schema**

En `backend/app/schemas/reporte.py`, añadir al final:

```python
class InventarioNivelOut(BaseModel):
    nombre: str
    unidad: str
    stock_actual: Decimal
    stock_minimo: Decimal
    nivel_pct: int
    bajo_minimo: bool
```

- [ ] **Step 4: Add the service function**

En `backend/app/services/reporte_service.py`, añadir `Insumo` al import `from app.models import (...)`, y añadir:

```python
def inventario_niveles(db: Session) -> list[dict]:
    out = []
    for i in db.query(Insumo).all():
        smin = float(i.stock_minimo)
        sact = float(i.stock_actual)
        if smin > 0:
            pct = min(100, round(sact / (2 * smin) * 100))
        else:
            pct = 100 if sact > 0 else 0
        out.append(
            {
                "nombre": i.nombre_insumo,
                "unidad": i.unidad.abreviatura,
                "stock_actual": i.stock_actual,
                "stock_minimo": i.stock_minimo,
                "nivel_pct": pct,
                "bajo_minimo": i.stock_actual < i.stock_minimo,
            }
        )
    out.sort(key=lambda x: x["nivel_pct"])
    return out
```

- [ ] **Step 5: Add the endpoint**

En `backend/app/api/v1/reportes.py`, añadir `InventarioNivelOut` al import de schemas y:

```python
@router.get("/inventario-niveles", response_model=list[InventarioNivelOut])
def inventario_niveles(
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.require_admin),
):
    return reporte_service.inventario_niveles(db)
```

- [ ] **Step 6: Run tests + full backend suite**

Run: `docker compose exec api pytest tests/test_reportes_api.py -v && docker compose exec api pytest`
Expected: PASS (nuevos + sin regresiones).

- [ ] **Step 7: Commit (local)**

```bash
git add backend/app/schemas/reporte.py backend/app/services/reporte_service.py \
        backend/app/api/v1/reportes.py backend/tests/test_reportes_api.py
git commit -m "feat(api): reportes/inventario-niveles"
```

---

## Task 3: Web — KPIs con delta (color por beneficio)

**Files:**
- Modify: `web/app/services/api_client.py`
- Modify: `web/app/dashboard/routes.py`
- Modify: `web/app/templates/dashboard/index.html`
- Modify: `web/app/static/css/app.css`
- Test: `web/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `api_gateway.call`, `rango_preset` (ya en el módulo).
- Produces:
  - `api_client.get_comparativo(access, desde, hasta) -> dict`.
  - `dashboard.routes._kpis(comp: dict) -> list[dict]` con cada tarjeta `{label, valor, delta, flecha, color, accent}` (`color ∈ {"up","down","neutral"}`).
  - El template pasa a recibir `kpis` (además de `serie`, `top`, `preset`, `desde`, `hasta`).

- [ ] **Step 1: Update the failing test**

Reemplazar en `web/tests/test_dashboard.py` la constante `RESUMEN` y el stub por un `COMPARATIVO`, y añadir los tests de color. Cambios:

Sustituir `RESUMEN = {...}` por:

```python
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
```

Sustituir la línea de `_stub_reportes` que hacía `get_reporte_resumen` por:

```python
    monkeypatch.setattr(api_client, "get_comparativo", lambda a, d, h: COMPARATIVO)
```

(Deja intactos los stubs de `get_ventas_por_dia` y `get_top_productos`.)

`test_dashboard_muestra_kpis` sigue válido (`$400.00`, `Utilidad`). Añadir al final del archivo:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `docker compose exec web pytest tests/test_dashboard.py -v`
Expected: FAIL — la ruta aún llama `get_reporte_resumen` (AttributeError en el stub eliminado) / no hay `kpi__delta`.

- [ ] **Step 3: Add the API client function**

Añadir a `web/app/services/api_client.py`:

```python
def get_comparativo(access, desde=None, hasta=None):
    r = requests.get(
        f"{_base()}/reportes/comparativo",
        headers=_headers(access),
        params={"desde": desde, "hasta": hasta},
        timeout=TIMEOUT,
    )
    return _check(r)
```

- [ ] **Step 4: Build `kpis` in the route**

En `web/app/dashboard/routes.py`, añadir el helper `_kpis` y usar `get_comparativo`. Reemplazar el cuerpo de `index()` para obtener `comparativo` y construir `kpis` (mantener `serie`/`top`):

```python
# (label, key, up_is_good|None, es_money, es_accent)
_KPI_DEFS = [
    ("Total vendido", "total_vendido", True, True, False),
    ("# Ventas", "num_ventas", True, False, False),
    ("Ticket promedio", "ticket_promedio", None, True, False),
    ("Gastos", "total_gastos", False, True, False),
    ("Compras", "total_compras", None, True, False),
    ("Utilidad estimada", "utilidad_estimada", True, True, True),
]


def _kpis(comp):
    actual, deltas = comp["actual"], comp["deltas"]
    tarjetas = []
    for label, key, up_good, money, accent in _KPI_DEFS:
        valor = f"${float(actual[key]):.2f}" if money else str(actual[key])
        delta = deltas.get(key) if up_good is not None else None
        if delta is None or delta == 0:
            flecha, color = "", "neutral"
        else:
            flecha = "▲" if delta > 0 else "▼"
            color = "up" if (delta > 0) == up_good else "down"
        tarjetas.append(
            {"label": label, "valor": valor, "delta": delta,
             "flecha": flecha, "color": color, "accent": accent}
        )
    return tarjetas
```

Y en `index()`, reemplazar la obtención de `resumen` y el `render_template`:

```python
    comp = api_gateway.call(api_client.get_comparativo, desde, hasta)
    serie = api_gateway.call(api_client.get_ventas_por_dia, desde, hasta)
    top = api_gateway.call(api_client.get_top_productos, desde, hasta)
    return render_template(
        "dashboard/index.html",
        kpis=_kpis(comp), serie=serie, top=top,
        preset=preset, desde=desde, hasta=hasta,
    )
```

- [ ] **Step 5: Render KPIs in the template**

En `web/app/templates/dashboard/index.html`, reemplazar toda la `<section class="kpis">…</section>` (las tarjetas fijas) por el bucle:

```html
<section class="kpis">
  {% for k in kpis %}
  <div class="kpi {{ 'kpi--accent' if k.accent }}">
    <span class="kpi__label">{{ k.label }}</span>
    <span class="kpi__value">{{ k.valor }}</span>
    {% if k.delta is not none %}
    <span class="kpi__delta kpi__delta--{{ k.color }}">{{ k.flecha }} {{ k.delta }}% vs periodo anterior</span>
    {% endif %}
  </div>
  {% endfor %}
</section>
```

- [ ] **Step 6: Add delta CSS**

Añadir a `web/app/static/css/app.css`:

```css
.kpi__delta { font-size: .72rem; margin-top: .25rem; }
.kpi__delta--up { color: var(--gain); }
.kpi__delta--down { color: var(--loss); }
.kpi__delta--neutral { color: var(--muted); }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker compose exec web pytest tests/test_dashboard.py -v`
Expected: PASS (incluidos los de color: Gastos+ → `down`, Ventas+ → `up`, y `$400.00`/`Utilidad`).

- [ ] **Step 8: Commit (local)**

```bash
git add web/app/services/api_client.py web/app/dashboard/routes.py \
        web/app/templates/dashboard/index.html web/app/static/css/app.css \
        web/tests/test_dashboard.py
git commit -m "feat(web): KPIs con variación vs periodo anterior (color por beneficio)"
```

---

## Task 4: Web — dona, tendencia diaria y barras de inventario

**Files:**
- Modify: `web/app/services/api_client.py`
- Modify: `web/app/dashboard/routes.py`
- Modify: `web/app/templates/dashboard/index.html`
- Modify: `web/app/static/css/app.css`
- Test: `web/tests/test_dashboard.py`

**Interfaces:**
- Consumes: `_kpis`, `serie`, `top` (Task 3); nuevo `api_client.get_inventario_niveles`.
- Produces: `get_inventario_niveles(access) -> list[dict]`; el template recibe también `inventario` (lista de niveles) y dibuja dona (`#chart-top`), línea de pedidos (`#chart-pedidos`) y barras de inventario.

- [ ] **Step 1: Write the failing test**

Añadir a `web/tests/test_dashboard.py`:

```python
INVENTARIO = [
    {"nombre": "Café en grano", "unidad": "kg", "stock_actual": 2.0,
     "stock_minimo": 5.0, "nivel_pct": 20, "bajo_minimo": True},
    {"nombre": "Leche", "unidad": "L", "stock_actual": 8.0,
     "stock_minimo": 4.0, "nivel_pct": 100, "bajo_minimo": False},
]
```

y actualizar `_stub_reportes` añadiendo (dentro de la función, junto a los otros stubs):

```python
    monkeypatch.setattr(api_client, "get_inventario_niveles", lambda a: INVENTARIO)
```

y añadir el test:

```python
def test_dashboard_dona_tendencia_e_inventario(client, monkeypatch):
    _login(client, monkeypatch)
    _stub_reportes(monkeypatch)
    cuerpo = client.get("/dashboard").get_data(as_text=True)
    assert "doughnut" in cuerpo               # tipo de la dona
    assert 'id="chart-pedidos"' in cuerpo     # línea de tendencia
    assert "Café en grano" in cuerpo          # barra de inventario
    assert "20%" in cuerpo                     # nivel_pct de la barra
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_dashboard.py::test_dashboard_dona_tendencia_e_inventario -v`
Expected: FAIL — no hay `doughnut`, `chart-pedidos` ni barras.

- [ ] **Step 3: Add the API client function**

Añadir a `web/app/services/api_client.py`:

```python
def get_inventario_niveles(access):
    r = requests.get(
        f"{_base()}/reportes/inventario-niveles",
        headers=_headers(access),
        timeout=TIMEOUT,
    )
    return _check(r)
```

- [ ] **Step 4: Fetch inventario in the route**

En `web/app/dashboard/routes.py`, dentro de `index()`, añadir el fetch y pasarlo al template:

```python
    inventario = api_gateway.call(api_client.get_inventario_niveles)
    return render_template(
        "dashboard/index.html",
        kpis=_kpis(comp), serie=serie, top=top, inventario=inventario,
        preset=preset, desde=desde, hasta=hasta,
    )
```

(Reemplaza el `return render_template(...)` de Task 3 por este, que añade `inventario`.)

- [ ] **Step 5: Update the template (dona + tendencia + inventario)**

En `web/app/templates/dashboard/index.html`, reemplazar la `<section class="graficas">…</section>` y el `<script>` de gráficas por:

```html
<section class="graficas">
  <div class="grafica"><h2>Ventas por día</h2><canvas id="chart-ventas"></canvas></div>
  <div class="grafica"><h2>Productos más vendidos</h2><canvas id="chart-top"></canvas></div>
  <div class="grafica"><h2>Tendencia de pedidos diarios</h2><canvas id="chart-pedidos"></canvas></div>
  <div class="grafica">
    <h2>Nivel de inventario</h2>
    <div class="inv">
      {% for i in inventario %}
      <div class="inv__row">
        <span class="inv__name">{{ i.nombre }}</span>
        <span class="inv__bar"><span class="inv__fill {{ 'inv__fill--low' if i.bajo_minimo }}" style="width:{{ i.nivel_pct }}%"></span></span>
        <span class="inv__pct">{{ i.nivel_pct }}%</span>
      </div>
      {% else %}<p class="muted">Sin insumos.</p>{% endfor %}
    </div>
  </div>
</section>

<script id="serie-data" type="application/json">{{ serie|tojson }}</script>
<script id="top-data" type="application/json">{{ top|tojson }}</script>
<script src="{{ url_for('static', filename='vendor/chart.umd.min.js') }}"></script>
<script>
  const serie = JSON.parse(document.getElementById("serie-data").textContent);
  const top = JSON.parse(document.getElementById("top-data").textContent);
  const cafe = ["#3a2a20", "#c8862f", "#8a5a12", "#6b4423", "#d9c9bb", "#a96f1f"];
  new Chart(document.getElementById("chart-ventas"), {
    type: "line",
    data: { labels: serie.map(p => p.fecha),
      datasets: [{ label: "Ventas ($)", data: serie.map(p => Number(p.total)),
        borderColor: "#c8862f", backgroundColor: "rgba(200,134,47,.15)", fill: true, tension: 0.3 }] },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
  new Chart(document.getElementById("chart-top"), {
    type: "doughnut",
    data: { labels: top.map(p => p.nombre),
      datasets: [{ data: top.map(p => Number(p.cantidad)), backgroundColor: cafe }] },
    options: { responsive: true, plugins: { legend: { position: "right" } } },
  });
  new Chart(document.getElementById("chart-pedidos"), {
    type: "line",
    data: { labels: serie.map(p => p.fecha),
      datasets: [{ label: "# Pedidos", data: serie.map(p => Number(p.num_ventas)),
        borderColor: "#3a2a20", backgroundColor: "rgba(58,42,32,.12)", fill: true, tension: 0.3 }] },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
</script>
```

- [ ] **Step 6: Add inventory-bar CSS**

Añadir a `web/app/static/css/app.css`:

```css
.inv { display: grid; gap: .55rem; }
.inv__row { display: grid; grid-template-columns: 130px 1fr 42px; align-items: center; gap: .5rem; font-size: .85rem; }
.inv__name { color: var(--ink-soft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.inv__bar { background: var(--bg); border-radius: 999px; height: 10px; overflow: hidden; }
.inv__fill { display: block; height: 100%; background: var(--accent); border-radius: 999px; }
.inv__fill--low { background: var(--loss); }
.inv__pct { text-align: right; color: var(--muted); font-variant-numeric: tabular-nums; }
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `docker compose exec web pytest tests/test_dashboard.py -v`
Expected: PASS — dona (`doughnut`), `chart-pedidos`, barras con `Café en grano`/`20%`, y los de Task 3 y el `chart-top`/`Café` previos.

- [ ] **Step 8: Full web suite + smoke**

Run: `docker compose exec web pytest`
Expected: PASS.

Smoke: `docker compose restart web`; con sesión admin en `localhost:5000/dashboard`, verificar KPIs con ▲/▼ (Gastos en rojo si sube), la dona, la línea de pedidos y las barras de inventario (rojas si bajo mínimo).

- [ ] **Step 9: Commit (local)**

```bash
git add web/app/services/api_client.py web/app/dashboard/routes.py \
        web/app/templates/dashboard/index.html web/app/static/css/app.css \
        web/tests/test_dashboard.py
git commit -m "feat(web): dona, tendencia de pedidos y nivel de inventario en Estadísticas"
```

---

## Definition of Done

- API: `GET /reportes/comparativo` (KPIs actual/anterior/deltas) y `GET /reportes/inventario-niveles`.
- Web Estadísticas: KPIs con ▲/▼ % y **color por beneficio** (Gastos ▲ = rojo), dona de productos, línea de tendencia de pedidos, y barras de nivel de inventario (rojas si bajo mínimo).
- La lógica de color vive en la ruta (`_kpis`), testeada (Gastos+ → down, Ventas+ → up).
- Suites backend y web en verde. Sin migraciones. Local (commits locales, sin push/PR).
- Fuera de alcance: rebanada "Otros" en la dona; capacidad real de almacén.
