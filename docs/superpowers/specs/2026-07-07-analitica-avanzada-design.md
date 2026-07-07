# Diseño — Analítica avanzada (widgets de Estadísticas)

**Fecha:** 2026-07-07
**Sprint:** 6 · backlog. Trabajo **local** (rama `feature/sprint6-backlog`, sin push/PR).
**Base:** endpoints de reportes del Slice A/B + panel web rediseñado.

---

## Objetivo

Enriquecer la página **Estadísticas** con: KPIs con variación vs periodo anterior,
dona de productos, tendencia de pedidos diarios y nivel de inventario. Arquitectura
Opción A (la API agrega; el web pinta). Sin migraciones.

## Sección 1 — Datos (backend)

### Endpoints nuevos (router `reportes`, `require_admin`)

- `GET /reportes/comparativo?desde&hasta` → KPIs actual vs periodo anterior:
  ```
  { actual:   {total_vendido, total_gastos, utilidad_estimada, num_ventas},
    anterior: {total_vendido, total_gastos, utilidad_estimada, num_ventas},
    deltas:   {total_vendido, total_gastos, utilidad_estimada, num_ventas} }
  ```
  - "Periodo anterior" = mismo número de días **inmediatamente previo** a `[desde, hasta]`:
    `n = (hasta - desde).days + 1`; `anterior = [desde - n días, desde - 1 día]`.
  - `delta` (porcentaje) = `round((actual - anterior) / anterior * 100, 1)`; si `anterior == 0`
    → `null` (la UI muestra "—"). Reutiliza `reporte_service.resumen` para ambos periodos.

- `GET /reportes/inventario-niveles` → foto actual de stock (sin fecha):
  ```
  [{ nombre, unidad, stock_actual, stock_minimo, nivel_pct, bajo_minimo }]
  ```
  - `nivel_pct = min(100, round(stock_actual / (2*stock_minimo) * 100))` si `stock_minimo > 0`;
    si `stock_minimo == 0` → `100` cuando `stock_actual > 0`, si no `0`.
  - `bajo_minimo = stock_actual < stock_minimo` (barra de alerta).
  - Ordenado por `nivel_pct` ascendente (los más críticos primero).

### Reusos (sin endpoint nuevo)
- **Dona de productos:** del `top-productos` existente; el `%` se calcula en el web sobre la
  suma del top-N mostrado (sin rebanada "Otros").
- **Tendencia de pedidos diarios:** del `ventas-por-dia` existente, campo `num_ventas`.

## Sección 2 — UI de Estadísticas

Layout (reorganiza lo existente):
- **KPIs:** las 6 tarjetas; en 4 (Total vendido, Gastos, Utilidad, # Ventas) se añade la
  variación **▲/▼ %** vs periodo anterior. Ticket promedio y Compras sin delta.
- **Gráficas fila 1:** *Ventas por día* (línea $, existente) + *Productos más vendidos*
  (**dona**, reemplaza la barra de top-productos).
- **Gráficas fila 2:** *Tendencia de pedidos diarios* (línea `num_ventas`) + *Nivel de
  inventario* (**barras horizontales** HTML/CSS: ancho = `nivel_pct`, rojas si `bajo_minimo`).

### Regla de color del delta (correctitud de negocio)

El color refleja el **beneficio para el negocio**, no el signo del delta:
- Cada KPI declara `up_is_good`: Total vendido, Utilidad, # Ventas → `True`; **Gastos → `False`**.
- **Flecha** = movimiento real (`▲` si `delta > 0`, `▼` si `delta < 0`).
- **Color** = `up` (verde) si `(delta > 0 and up_is_good)` o `(delta < 0 and not up_is_good)`;
  `down` (rojo) en el caso opuesto; `neutral` ("—") si `delta` es `null` o `0`.
- Consecuencia: **Gastos ▲ → rojo** (más egresos = alerta), **Gastos ▼ → verde** (ahorro);
  Ventas/Utilidad/# Ventas ▲ → verde.

**Dónde vive la lógica:** en la **ruta Flask**, no en Jinja. La ruta arma cada tarjeta como
`{label, valor, delta, flecha, color}` con `color ∈ {"up","down","neutral"}` ya resuelto; la
plantilla solo aplica la clase CSS. Esto evita condicionales frágiles en la plantilla y hace
la regla testeable de forma aislada.

## Sección 3 — Arquitectura y datos

- La ruta del dashboard (`dashboard.index`) pasa a pedir: `comparativo` (KPIs+deltas), `serie`
  (dos líneas), `top` (dona), `inventario-niveles` (barras). Se conserva el patrón cliente
  delgado (todo dato viene de la API).
- Chart.js (ya vendorizado) gana el tipo `doughnut` para la dona.
- Se mantiene la ruta `/dashboard` y sus asserts previos donde aplique.

## Sección 4 — Testing

- **Backend (pytest):**
  - `comparativo`: sembrar ventas fechadas en el periodo actual y en el anterior; verificar
    `actual`, `anterior`, y `deltas` (incluido `delta == null` cuando `anterior == 0`);
    `require_admin` → 403.
  - `inventario-niveles`: sembrar insumos; verificar `nivel_pct` (tope 100 y caso
    `stock_minimo == 0`), `bajo_minimo`, y el orden ascendente; 403.
- **Web (pytest):**
  - El dashboard renderiza las tarjetas con delta y los `<canvas>` de dona y tendencia, y las
    barras de inventario con su `%` (mock de `api_gateway`).
  - **Test de la regla de color:** una tarjeta de **Gastos con delta positivo** produce la
    clase de color "down" (rojo), y **Ventas con delta positivo** produce "up" (verde).

## Fuera de alcance (YAGNI)

- Rebanada "Otros" en la dona; comparativos por producto.
- Nivel de inventario con capacidad real de almacén (no existe el dato).
- Selección de qué KPIs mostrar (el mockup lo insinuaba); se muestran los fijos.
