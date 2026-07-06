# Diseño — Recetas y descuento automático de stock (feature/recetas)

**Fecha:** 2026-07-05
**Sprint:** 5 (slice 2 de 3: recetas + descuento automático)
**Rama:** `feature/recetas`

## Objetivo

Definir la receta de cada producto (`producto_insumo`) y descontar automáticamente el
stock de los insumos al confirmar un pedido, registrando el kárdex; y reponer el stock al
cancelar. Segundo slice del Sprint 5; el tercero son las compras. **Backend-only.**

Cubre RF de recetas y descuento automático de inventario.

## Contexto

- El esquema ya existe: `producto_insumo` (`cantidad_requerida`), `insumos`
  (`stock_actual`) y `movimientos_inventario` (kárdex: `tipo_movimiento`,
  `motivo`, `id_pedido`). Slice 1 añadió el CRUD de insumos y movimientos manuales.
- Punto de enganche: `pedido_service.crear` (arma líneas, pone la mesa Ocupada, hace
  commit) y `pedido_service.cancelar` (marca Cancelado, libera la mesa).

## Decisiones tomadas (brainstorming)

1. **Recetas: solo API** (Swagger); sin pantalla móvil en este slice.
2. **Stock insuficiente al crear pedido → bloquear (422)**; no se crea nada (consistente
   con el "no negativo" de los ajustes manuales del slice 1).
3. **Cancelar devuelve el stock** (reversa de las salidas del pedido).
4. Productos **sin receta** no descuentan nada (ni error).
5. **Autorización de recetas:** Cocinero / Administrador.

## Bloque 1 — API de recetas (`producto_insumo`)

La receta es un sub-recurso del producto.

| Método | Ruta | Descripción | Autorización |
|---|---|---|---|
| GET | `/productos/{id}/receta` | Líneas (insumo + cantidad requerida) | Cocinero / Admin |
| POST | `/productos/{id}/receta` | Añadir línea `{id_insumo, cantidad_requerida}` | Cocinero / Admin |
| DELETE | `/productos/{id}/receta/{id_producto_insumo}` | Quitar una línea | Cocinero / Admin |

Reglas de `POST`:
1. Rol ∈ {Cocinero, Administrador} → 403 si no.
2. Producto existe → 404 si no.
3. `id_insumo` existe → 422 si no.
4. `cantidad_requerida > 0` (422 vía schema).
5. El insumo no puede repetirse en la receta del producto → **409**.

`DELETE`: la línea debe existir y pertenecer al producto → 404 si no.

### Schemas (`schemas/receta.py`)

- `RecetaLineaCreate`: `{ id_insumo: int, cantidad_requerida: Decimal (gt=0) }`.
- `InsumoResumen`: `{ id_insumo, nombre_insumo, unidad: {abreviatura} }`.
- `RecetaLineaOut`: `{ id_producto_insumo, id_insumo, insumo: InsumoResumen,
  cantidad_requerida }`.

### Servicio (`services/receta_service.py`)

- `_check_rol(usuario)` — Cocinero/Admin (reutiliza el set `{"Cocinero", "Administrador"}`).
- `listar_receta(db, id_producto, usuario) -> list[ProductoInsumo]` — valida rol y producto.
- `agregar_linea(db, id_producto, data: RecetaLineaCreate, usuario) -> ProductoInsumo` —
  reglas de arriba.
- `eliminar_linea(db, id_producto, id_producto_insumo, usuario) -> None`.

Relación ORM: `ProductoInsumo.insumo = relationship("Insumo")` (con su `unidad`).

## Bloque 2 — Descuento automático y reposición

### Al crear pedido (`pedido_service.crear`)

Tras armar las líneas y hacer `flush` del pedido (para tener `id_pedido`), antes del commit:
1. Acumular el **requerido por insumo**:
   `requerido[id_insumo] += cantidad_requerida × item.cantidad` sobre las recetas de todos
   los productos del pedido.
2. Si algún insumo tiene `stock_actual < requerido` → **422** ("Stock insuficiente de
   <nombre>"); la transacción se revierte (no se crea el pedido, la mesa no queda Ocupada).
3. Si alcanza: por cada insumo, `stock_actual -= requerido` y se registra
   `MovimientoInventario(tipo_movimiento="Salida", motivo="Venta", id_pedido, id_insumo,
   id_usuario=el del pedido, cantidad=requerido)`.
4. Productos sin receta → no descuentan nada.

Todo en la **misma transacción** que la creación del pedido (atómico). El commit final ya
existe en `crear`.

### Al cancelar pedido (`pedido_service.cancelar`)

Antes del commit de la cancelación (que marca Cancelado y libera la mesa): por cada
movimiento **Salida/Venta** de ese pedido, registrar una **Entrada** (motivo `"Ajuste"`,
mismo `id_pedido`, `id_usuario` = quien cancela) y sumar de vuelta a `stock_actual`.

### Servicio (`services/receta_service.py`)

- `descontar_pedido(db, pedido, id_usuario) -> None` — pasos 1–4; lanza 422 si falta stock.
- `reponer_pedido(db, pedido, id_usuario) -> None` — reversa en la cancelación.

`pedido_service.crear` llama `receta_service.descontar_pedido(db, pedido, id_usuario)` tras
el `flush` y antes del `commit`. `pedido_service.cancelar` llama
`receta_service.reponer_pedido(db, pedido, usuario.id_usuario)` antes del `commit`.
Sin import circular: `pedido_service` → `receta_service` → modelos.

## Componentes

```
backend/app/
├── models/producto.py          # + relación ProductoInsumo.insumo
├── schemas/receta.py           # RecetaLineaCreate, InsumoResumen, RecetaLineaOut (nuevo)
├── services/receta_service.py  # CRUD receta + descontar_pedido + reponer_pedido (nuevo)
├── services/pedido_service.py  # crear/cancelar invocan al receta_service
└── api/v1/recetas.py           # rutas de receta (nuevo; en router.py, prefix /productos)
```

## Manejo de errores

| Situación | Código |
|---|---|
| Sin token | 401 |
| Rol ≠ Cocinero/Admin (recetas) | 403 |
| Producto o línea inexistente | 404 |
| Insumo inexistente o `cantidad_requerida ≤ 0` | 422 |
| Insumo duplicado en la receta | 409 |
| Crear pedido con stock insuficiente | 422 (pedido no creado) |

## Testing (`pytest`)

Helpers para crear insumo (vía API del slice 1, con `cocinero_headers`) y producto/mesa/
pedido (slices previos).

### Recetas CRUD
- Agregar línea → 201 con `insumo.nombre_insumo`; listar la trae; borrar → 204 y desaparece.
- Producto inexistente → 404; insumo inexistente → 422; `cantidad_requerida` 0 → 422;
  insumo duplicado → 409; rol Mesero → 403.

### Descuento automático
- Producto con receta (1 insumo, `cantidad_requerida`) y stock suficiente → crear pedido baja
  `stock_actual` en `cantidad_requerida × cantidad` y crea un movimiento Salida/Venta con el
  `id_pedido`.
- Producto **sin** receta → crear pedido no cambia ningún stock.
- Stock insuficiente → crear pedido **422**; el pedido no existe, el stock queda igual y la
  mesa sigue Disponible.

### Reposición
- Crear pedido (descuenta) → cancelar → `stock_actual` vuelve al valor previo y existe una
  Entrada (motivo Ajuste) por cada Salida del pedido.

## Fuera de alcance (YAGNI)

Editar la cantidad de una línea (se borra y re-agrega), recetas en móvil, compras (slice 3),
tocar inventario al cobrar/cancelar una venta ya cobrada (la cancelación de pedido es
pre-cobro), reportes (Sprint 6).
