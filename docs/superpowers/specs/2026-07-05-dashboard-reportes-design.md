# Diseño — Sprint 6: Dashboard y reportes

**Fecha:** 2026-07-05
**Sprint:** 6 (último) — Dashboard y reportes en el panel web admin (Flask).
**Metodología:** Opción A — la agregación vive en la API (FastAPI); el web solo pinta y exporta.

---

## Objetivo

Dar al administrador, desde el panel web, una vista de negocio: KPIs y gráficas del
periodo, más reportes filtrables de ventas y gastos exportables a PDF y XLSX.

## Decisión de arquitectura (Opción A)

Nuevos endpoints de agregación `GET /reportes/*` en FastAPI que agregan con SQL
(`GROUP BY`, `SUM`). El panel web (cliente delgado ya existente) consume esos JSON,
pinta KPIs/gráficas y genera los archivos de export a partir de los mismos datos.

Motivo: mantiene el patrón "web delgado / lógica en API", aprovecha que el IVA y el
desglose ya viven en el backend (testeado con pytest), y deja los reportes reutilizables
para el móvil a futuro. Se descartan agregar en Flask (rompe el patrón, duplica lógica)
y consultar la BD directo desde el web (rompe la separación API/BD).

---

## División en slices

### Slice A — Dashboard (PR #17)

**API — router nuevo `reportes` (solo lectura, `require_admin`):**

- `GET /reportes/resumen?desde&hasta` → KPIs del periodo:
  `{ total_vendido, num_ventas, ticket_promedio, total_gastos, total_compras, utilidad_estimada }`.
- `GET /reportes/ventas-por-dia?desde&hasta` → serie temporal para la gráfica:
  `[{ fecha, total, num_ventas }]`.
- `GET /reportes/top-productos?desde&hasta&limite=10` → ranking:
  `[{ id_producto, nombre, cantidad, importe }]`.

**Web:**

- Blueprint nuevo `dashboard` con ruta `/dashboard`.
- Selector de periodo: **Hoy / 7 días / Este mes / rango personalizado** (los presets solo
  calculan el par `desde`/`hasta`).
- Tarjetas de KPI (resumen).
- **Chart.js** vendorizado localmente en `web/app/static/vendor/chart.umd.min.js`
  (el web no tiene bundler ni CDN garantizado): una gráfica de línea (ventas/día) y una
  de barras (top productos).
- `index()` pasa a redirigir a `/dashboard`; se añaden enlaces "Dashboard" y "Reportes"
  al `nav` de `base.html`.

### Slice B — Reportes filtrables + export (PR #18)

**API — endpoints de detalle listable (mismo router, `require_admin`):**

- `GET /reportes/ventas?desde&hasta` → detalle de ventas:
  `[{ folio, fecha, mesa, total, metodos }]`.
- `GET /reportes/gastos?desde&hasta` → detalle de gastos:
  `[{ fecha, categoria, concepto, monto }]`.

**Web:**

- Rutas `/reportes/ventas` y `/reportes/gastos` con filtro por rango de fechas y tabla.
- Botones **Exportar PDF / Exportar XLSX** vía `?formato=pdf|xlsx`.
- Generación: **openpyxl** (XLSX) + **ReportLab** (PDF). ReportLab es pip puro, sin
  dependencias nativas (se evita WeasyPrint/GTK en el Dockerfile del web).
- El PDF/XLSX lleva encabezado con el rango y fila de totales.

---

## Contrato de datos / semántica

- **Fechas:** `desde` y `hasta` como `YYYY-MM-DD`, ambos inclusive; `hasta` se interpreta
  como fin de día. Si faltan, el default es **hoy**. Se filtra por `fecha_venta`,
  `fecha_gasto` y `fecha_compra` según el reporte.
- **Utilidad estimada:** `total_vendido − total_gastos − total_compras` en el rango. Se
  documenta como *estimada* (no resta el costo de venta por receta; no es contabilidad
  formal). Consistente con la deuda técnica ya anotada (costo = último, no promedio).
- **Top productos:** join `ventas → pedidos → detalle_pedido → productos`, agregando
  `cantidad` (SUM) e `importe` (SUM de `subtotal`), ordenado por cantidad desc.
- **Ventas por método:** una venta puede tener varios pagos (pago dividido); el reporte de
  detalle lista los métodos aplicados como texto concatenado.

## Autorización

Todos los `GET /reportes/*` requieren rol **Admin** (`require_admin`). El dashboard y los
reportes del web quedan detrás de `flask-login`, igual que el resto del panel.

## Testing

- **Backend (pytest, TDD):** por endpoint, sembrar ventas/gastos/compras en fechas
  conocidas y verificar los agregados (totales, ticket promedio, orden del top, filtro de
  rango) y que no-admin recibe **403**.
- **Web (pytest):** `/dashboard` y `/reportes/*` responden 200 autenticado / redirigen sin
  sesión; el export devuelve el `Content-Type` correcto (`application/pdf`,
  `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`); se mockea
  `api_gateway` (patrón de `test_usuarios.py`).

## Fuera de alcance (YAGNI)

- Distribución por método de pago / categoría en el dashboard (no priorizada).
- CRUD de catálogo en la web (deuda técnica aparte).
- Reportes programados / envío por correo.
- Contabilidad formal / costo de venta exacto por receta.
