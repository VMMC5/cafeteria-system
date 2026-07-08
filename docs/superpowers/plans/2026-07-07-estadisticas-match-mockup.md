# Plan — Estadísticas: igualar el mockup `stats.png`

**Fecha:** 2026-07-07 · **Rama:** `feature/sprint6-backlog` (LOCAL) · **Base:** `fb77373`
**Origen:** el plan `2026-07-07-analitica-avanzada.md` ya está 100% implementado (commits 5bd67af, 318cc73, 23a44dd, d181e19). Este plan es un **refinamiento de UI dirigido** para que la pantalla `/dashboard` (Estadísticas) coincida con el mockup aprobado `stats.png`. NO re-hace las Tareas 1-4 originales.

## Referencia visual (stats.png) — obligatoria para tareas de UI
- **Paleta:** café oscuro (`#3a2a20`), fondo crema/beige (`#d9c9bb` y claros), acentos mostaza/dorado (`#c8862f`, `#a96f1f`, `#8a5a12`). Ya existe la constante `cafe = [...]` en `dashboard/index.html`; reutilizarla.
- **KPIs:** tipografía grande para montos; lógica de color del delta ESTRICTA — verde = incremento bueno, rojo = incremento de gastos (ya implementada en `dashboard/routes.py::_kpis`, respetar, no romper).
- **Charts (Chart.js, vendorizado local `vendor/chart.umd.min.js`):**
  - "Ventas vs Gastos" = **barras agrupadas** (2 series).
  - Dona "Productos más vendidos" = **leyenda personalizada con %** + **total al centro** (plugin inline de Chart.js para el texto central).
  - "Tendencia de pedidos diarios" = **línea con área rellena por gradiente suave**.
- **Inventario:** barras horizontales HTML/CSS (ya implementadas; conservar).

## Global Constraints
- No romper los tests existentes (backend 178, web 40). Cada tarea agrega/actualiza tests.
- No tocar backend salvo lo que la Tarea 1 especifica. No cambiar la lógica de color de KPIs.
- Chart.js solo desde el vendor local (CSP/offline). Plugins = inline en el `<script>`, no CDN.
- Mantener el patrón web: ruta Flask → `api_gateway.call(api_client.*)` → template Jinja con datos vía `<script type="application/json">`.

---

## Task 1 — Backend: `GET /reportes/gastos-por-dia`
**Por qué:** la gráfica "Ventas vs Gastos" necesita una serie de gastos alineada por fecha; hoy solo existe `ventas-por-dia`.
**Alcance (mirror exacto de `ventas-por-dia`):**
- `reporte_service.gastos_por_dia(db, desde, hasta) -> list[dict]`: agrupa `Gasto.monto` por `func.date(Gasto.fecha_gasto)` dentro del rango, `order_by` fecha. Devuelve `[{fecha, total, num_gastos}]`. (Espejo de `ventas_por_dia`, sin filtro de estado — los gastos no tienen estado.)
- Schema `GastoPorDiaOut(BaseModel)`: `fecha: date`, `total: Decimal`, `num_gastos: int`.
- Endpoint `GET /reportes/gastos-por-dia` con `desde/hasta` opcionales, `require_admin`, usando `reporte_service.rango(...)`.
- `api_client.get_gastos_por_dia(access, desde=None, hasta=None)` (espejo de `get_ventas_por_dia`).
**Tests (backend, TDD):** en `tests/test_reportes_api.py` (o archivo nuevo si más limpio): 401 sin auth; agrupa por día correctamente sobre datos sembrados; respeta el rango; devuelve `num_gastos` y `total` correctos; vacío → `[]`.
**Archivos:** `backend/app/services/reporte_service.py`, `backend/app/schemas/reporte.py`, `backend/app/api/v1/reportes.py`, `web/app/services/api_client.py`, tests backend.

## Task 2 — Web: gráfica "Ventas vs Gastos" (barras agrupadas)
**Por qué:** el mockup reemplaza la línea de "Ventas por día" por barras agrupadas Ventas vs Gastos.
**Alcance:**
- Ruta `dashboard/routes.py`: además de `serie` (ventas por día), obtener `gastos_por_dia` y construir una estructura alineada por fecha `serie_vg = [{fecha, ventas, gastos}]` (unir por fecha; fechas sin gasto → 0, fechas sin venta → 0).
- Template: reemplazar el canvas/`Chart` de "Ventas por día" por **"Ventas vs Gastos"** tipo `bar` con 2 datasets (Ventas = mostaza `#c8862f`, Gastos = café oscuro `#3a2a20` — igual que el mockup), `barPercentage`/`categoryPercentage` para barras agrupadas, leyenda arriba mostrando "Ventas"/"Gastos".
- Título de la tarjeta: "Ventas vs Gastos".
**Tests (web):** `web/tests/test_dashboard.py` — la página incluye el canvas de Ventas vs Gastos y ambos datasets; la ruta pasa `serie_vg` no vacío con datos demo (mock del gateway como en tests existentes).
**Archivos:** `web/app/dashboard/routes.py`, `web/app/templates/dashboard/index.html`, tests web.

## Task 3 — Web: dona (centro + leyenda %) y tendencia (gradiente)
**Alcance:**
- **Dona** "Productos más vendidos": plugin **inline** de Chart.js que dibuja el **total al centro** (suma de cantidades + etiqueta, p.ej. "N\npedidos"); **leyenda personalizada** (HTML al costado) que lista cada producto con su **porcentaje** del total (como el mockup: nombre + %). Paleta `cafe`.
- **Tendencia de pedidos diarios**: línea con **relleno de gradiente vertical** suave (crear `CanvasGradient` en el callback de `backgroundColor` usando el `ctx` del chart), color mostaza translúcido → transparente.
**Tests (web):** presencia del plugin de texto central / contenedor de leyenda con %; el canvas de tendencia sigue presente. (Aserciones sobre el HTML/JS renderizado, específicas — evitar coincidencias frágiles.)
**Archivos:** `web/app/templates/dashboard/index.html` (+ ruta si la leyenda % necesita datos precomputados), tests web.

## Task 4 — Web: chrome del panel (indicadores, presets, exportar)
**Alcance:**
- **Chips "Indicadores a mostrar"**: toggles (Ventas, Gastos, Ganancia, Pedidos, Productos top, Inventario, Tickets promedio) que muestran/ocultan las secciones correspondientes (vía querystring o toggle CSS/JS simple). Estado activo estilo pill café.
- **Presets de periodo alineados al mockup**: Mes / 6 meses / Año / Rango. Extender `rango_preset` en `dashboard/routes.py`. Para "6 meses"/"Año", definir el bucketing de la gráfica de barras (mensual) — documentar y testear la agregación.
- **Botón "Exportar vista"** arriba a la derecha (enlace a `/reportes` o export existente; sin inventar backend nuevo).
**Tests (web):** presets nuevos devuelven rangos correctos; los chips filtran secciones; el botón existe.
**Archivos:** `web/app/dashboard/routes.py`, `web/app/templates/dashboard/index.html`, tests web.
> Nota de diseño (resolver antes de ejecutar Task 4): confirmar con el usuario el comportamiento del bucketing mensual para "6 meses"/"Año" y si los chips filtran por servidor o cliente.

---

## Orden y checkpoints
Ejecución **subagent-driven**, un subagente por tarea, con **pausa de revisión con el usuario entre cada tarea**. Tras cada tarea: implementador (TDD) → revisor de tarea → fix loop → commit local → reporte al usuario → esperar visto bueno para la siguiente.
