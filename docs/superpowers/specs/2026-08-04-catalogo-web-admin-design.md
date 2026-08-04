# Spec — CRUD de catálogo en la web admin

**Fecha:** 2026-08-04 · **Alcance:** solo `web/` (Flask). Sin cambios en la API.

## Objetivo

Cerrar el pendiente "CRUD de catálogo en la web admin": gestionar **productos, categorías y mesas** desde el panel (hoy solo vía Swagger). La API ya expone el CRUD completo de las tres entidades (lectura autenticada, escritura `require_admin`); el panel es admin-only, así que no hay trabajo de autorización nuevo.

## Decisiones tomadas (brainstorming)

1. **Alcance:** los 3 CRUDs (productos, categorías, mesas) en una sola rebanada.
2. **Navegación:** un solo ítem "Catálogo" en el sidebar que abre `/catalogo` con pestañas Productos | Categorías | Mesas.
3. **Borrado — reflejar la semántica de la API:**
   - Productos: **toggle Disponible/No disponible** (la API hace soft-delete); sin botón eliminar.
   - Mesas y categorías: **Eliminar** real con `confirm()`; si la API rechaza por referencias FK, el detalle se muestra como flash de error.
4. **Estado de mesa:** editable solo entre **Disponible ⇄ Reservada**. Una mesa **Ocupada** muestra su estado como badge solo-lectura y el form no envía `estado` (la ocupación/liberación la maneja el flujo pedido→cobro).
5. **Estructura:** un blueprint `catalogo` con 3 sub-recursos (no 3 blueprints, no SPA con tabs cliente).

## Arquitectura

- **Blueprint** `web/app/catalogo/` (`__init__.py` + `routes.py`), registrado en `web/app/__init__.py`. Patrón idéntico a `usuarios`: `@login_required`, `api_gateway.call(api_client.<fn>, ...)`, flash + redirect/re-render.
- **`api_client.py`**: 14 funciones nuevas calcadas del estilo existente — `list/get/create/update` para las 3 entidades (list de productos acepta `id_categoria` y `disponible`) + `delete_categoria` y `delete_mesa`. Productos no necesita `delete`: el toggle usa `update_producto` (PATCH).
- **Sidebar** (`base.html`): ítem "Catálogo" entre Usuarios y Reportes, activo con `request.endpoint.startswith('catalogo.')`.
- **Recordar (WSL2):** tras registrar el blueprint, `docker compose restart web` (el hot-reload no recarga rutas).

### Rutas

| Ruta | Acción |
|---|---|
| `GET /catalogo` | redirect a `/catalogo/productos` |
| `GET /catalogo/productos` | lista + filtros (categoría, disponibilidad) |
| `GET /catalogo/productos/nuevo` · `POST /catalogo/productos` | alta |
| `GET /catalogo/productos/<id>/editar` · `POST /catalogo/productos/<id>` | edición |
| `POST /catalogo/productos/<id>/toggle` | PATCH `{disponible: !actual}` |
| `GET /catalogo/categorias` (+ nuevo/editar/POST) | CRUD categorías |
| `POST /catalogo/categorias/<id>/eliminar` | DELETE (FK-safe en API) |
| `GET /catalogo/mesas` (+ nuevo/editar/POST) | CRUD mesas |
| `POST /catalogo/mesas/<id>/eliminar` | DELETE (FK-safe en API) |

## Vistas (templates/catalogo/)

- `_tabs.html`: pestañas compartidas, estilo del tema "Cafetería Aroma", incluidas arriba de cada lista.
- **Productos** — `productos_list.html`: nombre, categoría, precio, badge Disponible/No disponible, acciones Editar/Toggle; filtros por categoría y estado. `productos_form.html`: nombre, descripción (opcional), categoría (dropdown de `list_categorias`), precio (`input number step=0.01 min=0`), checkbox disponible.
- **Categorías** — lista nombre + descripción; form de 2 campos; Eliminar con `confirm()`.
- **Mesas** — lista número, capacidad, ubicación, badge de estado (verde Disponible / rojo Ocupada / ámbar Reservada); form número, capacidad (`min=1`), ubicación (opcional), selector de estado limitado a Disponible/Reservada, oculto (badge solo-lectura) si la mesa está Ocupada.

**Decimal:** la API serializa `Decimal` como **string**; el precio se interpola tal cual (`$ {{ p.precio_venta }}`) sin `float()`, salvo necesidad real de comparar/ordenar.

## Errores y validación

- Alta/edición con error de API: `flash(e.detail, "error")` + re-render del form con el `status_code` de la API y `form=request.form` (valores preservados). Igual que Usuarios.
- Eliminar/toggle con error: flash + redirect a la lista (caso clave: categoría con productos o mesa referenciada → la API responde error FK y el panel solo lo informa).
- Validación fuerte en la API (Pydantic); el form aporta `required`/`min`/`step` como primera barrera.

## Tests (`web/tests/test_catalogo.py`)

Patrón de `test_usuarios.py`: `api_client` stubbeado (monkeypatch), **Decimal como string en los stubs**. Cobertura mínima:

- Render de las 3 listas; filtros de productos pasan los params correctos.
- Alta y edición: caso feliz (redirect + flash info) y error de API (re-render + flash error + status propagado), por entidad.
- Toggle de producto manda `{disponible: not actual}`.
- Eliminar categoría/mesa: éxito y rechazo FK (flash de error, lista sigue viva).
- Mesa Ocupada: el form no envía `estado`; el template no ofrece el selector.
- Sin sesión → redirect a login.

Metodología: TDD (test primero por sub-recurso), como el resto del proyecto.

## Fuera de alcance

- Cambios en la API (endpoints, semántica de borrado, promedio de costos, etc.).
- Gestión de recetas (`producto_insumo`) — sigue por API; candidato a rebanada futura.
- Imágenes de producto (no existen en el modelo).
- Paginación de listas (los catálogos son pequeños; consistente con Usuarios).
