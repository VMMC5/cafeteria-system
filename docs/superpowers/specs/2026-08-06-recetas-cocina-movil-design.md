# Spec — Recetas en el módulo Cocina (móvil)

**Fecha:** 2026-08-06 · **Estado:** aprobado en brainstorming

## Objetivo

Cerrar el pendiente "Recetas se gestionan solo por API (Swagger); sin pantalla móvil": el Cocinero (o Administrador) puede ver y editar la receta de cada producto — qué insumos lleva y en qué cantidad — desde el módulo Cocina de la app.

## Decisiones tomadas (brainstorming)

- **Gestión completa** (ver, agregar, editar cantidad, eliminar líneas), no solo consulta.
- **Navegación lista → detalle**: entrada "Recetas" en el menú de Cocina → lista de productos con búsqueda → detalle de receta del producto.
- **Edición inline** en el detalle (sin modal): tocar la cantidad la vuelve editable; formulario fijo al pie para agregar línea.
- **PATCH nuevo en la API** para editar cantidad (único cambio de backend). Se descartó DELETE+POST encadenado por no ser atómico.
- **Sin conteo de líneas en la lista** de productos: `GET /productos` no lo trae y no vale N requests ni tocar ese endpoint. El nº de líneas se ve al entrar al detalle. Mejora futura si se extraña.

## Backend — `PATCH /productos/{id_producto}/receta/{id_insumo}`

- Body: `{"cantidad_requerida": Decimal > 0}` (mismo `Field(gt=0)` que el create; nuevo schema `RecetaLineaUpdate`).
- Respuesta 200: la línea actualizada (`RecetaLineaOut`).
- Reusa `_check_rol` (Cocinero/Administrador → si no, 403) y `_producto_or_404` de `receta_service`.
- 404 si el producto no existe o la línea (producto, insumo) no existe; 422 si la cantidad es ≤ 0.
- Servicio: `receta_service.actualizar_linea(db, id_producto, id_insumo, data, usuario)`.

## API-client móvil (`src/api/client.ts`)

Tipos `RecetaLinea { id_producto_insumo, id_insumo, insumo: { id_insumo, nombre_insumo, unidad: { abreviatura } }, cantidad_requerida }`. `cantidad_requerida` llega como **string** (Decimal serializado) y se coacciona con el patrón de `coerce.ts`.

Funciones nuevas (con `authCfg` como las existentes):
- `getReceta(access, idProducto): Promise<RecetaLinea[]>`
- `addRecetaLinea(access, idProducto, { id_insumo, cantidad_requerida })` — la cantidad se envía como string.
- `patchRecetaLinea(access, idProducto, idInsumo, cantidad)` — idem.
- `deleteRecetaLinea(access, idProducto, idInsumo)` — 204 sin cuerpo.

`getProductos` y `getInsumos` ya existen; no se tocan.

## Lógica pura (`src/lib/recetas.ts`)

- `cantidadValida(txt): boolean` — número > 0, hasta 3 decimales (lo que acepta la API), acepta coma o punto decimal.
- `filtrarProductos(productos, query)` — filtro por nombre, case/acento-insensible (mismo criterio de búsqueda usado en otras listas si existe helper; si no, `toLowerCase` + `normalize`).
- `insumosDisponibles(insumos, receta)` — excluye del selector los insumos ya presentes en la receta (previene el 400 de duplicado en lugar de provocarlo).
- `aPayloadLinea(idInsumo, cantidadTxt)` — normaliza coma→punto y arma el payload con la cantidad como string.

## UI

### `src/app/cocina/recetas.tsx` — lista
- Entrada nueva "Recetas" en el menú de `cocina/index.tsx` (mismo patrón que Compras/Inventario).
- Lista de productos (solo nombre: el type `Producto` del client trae `id_categoria` numérico, no el nombre de la categoría) con búsqueda por nombre arriba.
- Tocar un producto navega a `/cocina/receta-detalle?id_producto=<id>&nombre=<nombre>` (mismo patrón de query params + `useLocalSearchParams` que Inventario → Ajuste).

### `src/app/cocina/receta-detalle.tsx` — detalle
- Header con el nombre del producto y badge "N insumos" (contado de la receta cargada; "Sin receta" si 0).
- Cada línea: nombre del insumo, cantidad + abreviatura de unidad, ✖ para eliminar (con `Alert` de confirmación).
- Tocar la cantidad → input numérico con ✓ (PATCH) y cancelar.
- Pie fijo "Agregar insumo": selector de insumo (solo `insumosDisponibles`) + input de cantidad + botón Agregar (POST).
- Tras cada mutación exitosa se recarga la receta desde la API (fuente de verdad).

## Errores y estados

Mismo manejo que Compras/Inventario: spinner de carga; si el GET falla, mensaje con botón Reintentar; errores de mutación en `Alert` mostrando el `detail` de la API; botones deshabilitados mientras hay una operación en vuelo (sin dobles envíos).

## Tests (TDD)

- **Backend** (`test_recetas_api.py`): PATCH feliz (cambia cantidad y responde la línea), 404 producto inexistente, 404 línea inexistente, 422 cantidad ≤ 0, 403 rol no autorizado (Mesero).
- **Móvil** (`src/lib/recetas.test.ts` + `src/api/client.test.ts`): `cantidadValida` (enteros, decimales, coma, 0, negativo, >3 decimales, texto), `filtrarProductos` (acentos, mayúsculas, query vacía), `insumosDisponibles` (excluye presentes, lista vacía), `aPayloadLinea` (coma→punto, string); las 4 funciones del client con stubs **Decimal-string** (convención del proyecto).
- Pantallas: smoke manual con la API local (login Cocinero → Recetas → agregar/editar/eliminar línea), como el resto de pantallas del móvil.

## Fuera de alcance

- Conteo de líneas de receta en la lista de productos (requeriría tocar `GET /productos`).
- Crear/editar insumos desde esta pantalla (ya existe Inventario para eso).
- Costeo de receta (costo por producto según insumos) — candidato a slice futuro de reportes.
- Descuento de inventario al vender: ya existe (`requerido_y_validar`/`aplicar_descuento`), esta pantalla no lo toca.
