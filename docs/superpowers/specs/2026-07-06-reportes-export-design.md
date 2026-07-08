# Diseño — Slice B: Reportes filtrables + export (PDF/XLSX)

**Fecha:** 2026-07-06
**Sprint:** 6 · Slice B. Trabajo **local** (rama `feature/sprint6-backlog`, sin push/PR por ahora).
**Base:** endpoints de agregación del Slice A (`/reportes/*`) + panel web rediseñado ("Cafetería Aroma").

---

## Objetivo

Dar al administrador una página **Reportes** en el panel web para consultar el detalle de
**ventas** y **gastos** por rango de fechas, con **vista previa** en pantalla y **descarga
en PDF y XLSX**. Alcance MVP del spec original, presentado con el layout del mockup
(panel de configuración + vista previa + descargar).

## Decisiones tomadas

- **Alcance:** solo reportes de **Ventas** y **Gastos** (detalle). Se difieren los tipos
  Productos/Inventario/Pedidos y los filtros de categoría/usuario/método/agrupar-por, y la
  gráfica embebida en el reporte.
- **Una sola página** `/reportes` con selector de **tipo** (Ventas | Gastos), no dos rutas.
- **PDF con WeasyPrint** (reusa plantilla Jinja) + **XLSX con openpyxl**. Se modifica el
  Dockerfile del web para las libs nativas de WeasyPrint.
- Arquitectura **Opción A** (Slice A): la API agrega/lista; el web pinta y genera los
  archivos. Sin migraciones.

---

## Sección 1 — Página y endpoints

### Web — página única `/reportes` (blueprint `reportes`, `@login_required`)
- **Panel de configuración:** selector **Tipo** (Ventas | Gastos), **rango de fechas**
  (pills Hoy / 7 días / Este mes / Rango + inputs `desde`/`hasta`, reusando `rango_preset`),
  y **formato** de descarga (PDF | XLSX).
- **Vista previa:** tabla del reporte con encabezado (rango) y **fila de totales**.
- **Descargar PDF / Descargar XLSX** vía `?formato=pdf|xlsx`.
- Se agrega **"Reportes"** como tercer ítem del sidebar (`base.html`).

### API — endpoints de detalle (router `reportes`, `require_admin`)
- `GET /reportes/ventas?desde&hasta` → `[{ folio, fecha, mesa, total, metodos }]`
  - `folio` del ticket; `mesa` = `numero_mesa` del pedido; `total` de la venta; `metodos` =
    nombres de método de pago concatenados (soporta pago dividido).
  - Solo ventas `estado_venta == "Completada"`; filtro de fechas inclusivo por `func.date`.
- `GET /reportes/gastos?desde&hasta` → `[{ fecha, categoria, concepto, monto }]`
  - `categoria` = `nombre_categoria`; filtro por `func.date(fecha_gasto)`.
- Reglas de fecha (default hoy, ambos inclusive) idénticas al Slice A vía
  `reporte_service.rango`.

## Sección 2 — Export e infraestructura

La ruta `/reportes` recibe `?tipo&desde&hasta&formato`. Sin `formato`, renderiza la vista
previa HTML. Con `formato`:
- **XLSX (openpyxl):** libro construido en memoria (encabezado con rango, tabla, fila de
  totales); respuesta con
  `Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` y
  `Content-Disposition: attachment; filename="reporte-<tipo>-<desde>_<hasta>.xlsx"`.
- **PDF (WeasyPrint):** renderiza una plantilla Jinja de impresión (misma tabla + totales)
  a bytes PDF; respuesta `application/pdf` como adjunto.

**Infraestructura (local, sin push):**
- `web/requirements.txt`: `+ WeasyPrint`, `+ openpyxl`.
- `web/Dockerfile`: `apt-get install` de las libs nativas de WeasyPrint
  (`libpango-1.0-0`, `libpangocairo-1.0-0`, `libcairo2`, `libgdk-pixbuf-2.0-0`,
  `libffi-dev`, `shared-mime-info`).
- Reconstruir la imagen: `docker compose build web` y reiniciar.

### Estructura de archivos
- API: extender `backend/app/schemas/reporte.py` (`VentaDetalleOut`, `GastoDetalleOut`),
  `backend/app/services/reporte_service.py` (`detalle_ventas`, `detalle_gastos`),
  `backend/app/api/v1/reportes.py` (2 endpoints). Tests en `backend/tests/test_reportes_api.py`.
- Web: `web/app/services/api_client.py` (`get_reporte_ventas`, `get_reporte_gastos`);
  blueprint `web/app/reportes/routes.py` + registro en `web/app/__init__.py`;
  `web/app/services/export.py` (helpers `to_xlsx`, `to_pdf`);
  plantillas `web/app/templates/reportes/index.html` y `web/app/templates/reportes/print.html`;
  enlace en `web/app/templates/base.html`. Tests en `web/tests/test_reportes.py`.

## Sección 3 — Testing

- **Backend (pytest):** por endpoint, sembrar ventas/gastos en fechas conocidas y verificar
  el detalle (folio/mesa/total/métodos; categoría/concepto/monto), el filtro de rango,
  `require_admin` → 403 y 401 sin token.
- **Web (pytest):** `/reportes` renderiza la vista previa (mock de `api_gateway`);
  `?formato=xlsx` responde con el `Content-Type` de spreadsheet y cabecera `attachment`;
  `?formato=pdf` responde `application/pdf`. Corren dentro del contenedor `web` (con
  WeasyPrint instalado tras el rebuild).

## Fuera de alcance (YAGNI — diferido)

- Tipos de reporte Productos/Inventario/Pedidos.
- Filtros de categoría / usuario / método de pago / agrupar-por.
- Gráfica embebida dentro del reporte.
- Programación/envío por correo de reportes.
