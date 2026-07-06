# Diseño — Insumos: inventario y ajustes (API + móvil) (feature/insumos)

**Fecha:** 2026-07-05
**Sprint:** 5 (slice 1 de 3: insumos)
**Rama:** `feature/insumos`

## Objetivo

Gestionar insumos y su stock: CRUD de insumos (con unidad de medida), consulta de
inventario con alerta de mínimo, y registro de ajustes/mermas que mueven el stock y
alimentan el kárdex. Primer slice del Sprint 5 (inventario y compras); los siguientes son
recetas + descuento automático (slice 2) y compras (slice 3).

Cubre RF de inventario (insumos y movimientos manuales).

## Contexto

El esquema ya existe (Sprint 0): `insumos` (`stock_actual`, `stock_minimo`,
`costo_unitario`), `unidades_medida` (sembrado: Gramo, Kilogramo, Mililitro, Litro, Pieza)
y `movimientos_inventario` (kárdex: `tipo_movimiento` Entrada/Salida, `motivo`
Compra/Venta/Ajuste/Merma/Inicial, con `id_pedido`/`id_compra`). No hay migración.

## Visión del Sprint 5 (contexto)

| Slice | Contenido | Estado |
|---|---|---|
| **1 — Insumos** | CRUD insumos + inventario móvil con alertas + ajustes/merma | este spec |
| 2 — Recetas + descuento | `producto_insumo` + descuento automático de stock al confirmar pedido | pendiente |
| 3 — Compras | proveedores + registrar compra (entrada de stock) | pendiente |

## Decisiones tomadas (brainstorming)

1. **Superficie:** API + móvil Cocina (el rol Cocinero es "Preparación e inventario").
2. **Autorización:** insumos y movimientos → **Cocinero / Administrador** (guard por rol en
   el servicio). El catálogo de unidades es de solo lectura para cualquier autenticado.
3. **Stock:** cada movimiento actualiza `stock_actual` y registra el kárdex; una
   Salida/Merma mayor al stock → **422** (no se permite negativo).
4. **Móvil:** ver inventario (con alerta de mínimo) + registrar ajuste/merma. Crear/editar
   insumos queda por API.

## API (`/api/v1`)

| Método | Ruta | Descripción | Autorización |
|---|---|---|---|
| GET | `/unidades` | Catálogo de unidades de medida | autenticado |
| GET | `/insumos` | Lista de insumos (con unidad y stock) | Cocinero / Admin |
| GET | `/insumos/{id}` | Detalle | Cocinero / Admin |
| POST | `/insumos` | Alta de insumo | Cocinero / Admin |
| PATCH | `/insumos/{id}` | Editar (no el stock) | Cocinero / Admin |
| POST | `/insumos/{id}/movimientos` | Registrar ajuste/merma | Cocinero / Admin |

### Movimientos (`registrar_movimiento`)

Entrada (`MovimientoCreate`): `{ tipo, motivo, cantidad }`.
1. Rol ∈ {Cocinero, Administrador}; si no → **403**.
2. Insumo existe → **404** si no.
3. `tipo ∈ {Entrada, Salida}`, `motivo ∈ {Ajuste, Merma}`, `cantidad > 0` (**422** vía
   schema/validación).
4. **Entrada** → `stock_actual += cantidad`; **Salida** → `stock_actual -= cantidad`.
5. Si `tipo == Salida` y `cantidad > stock_actual` → **422** (no negativo).
6. Registra `MovimientoInventario(id_insumo, id_usuario=actual, tipo_movimiento=tipo,
   motivo, cantidad)`; commit.
7. Devuelve el **insumo actualizado** (`InsumoOut`) para que el móvil vea el nuevo stock.

Notas: `stock_actual` solo cambia por movimientos; en el alta es el saldo inicial. Los
motivos `Compra`/`Venta`/`Inicial` los generará el sistema (slices 2/3); aquí solo se
permiten `Ajuste`/`Merma` manuales.

## Schemas (`schemas/insumo.py`)

- `UnidadOut`: `{ id_unidad, nombre_unidad, abreviatura }`.
- `InsumoCreate`: `{ nombre_insumo: str (min_length=1), id_unidad: int,
  descripcion: str | None = None, stock_actual: Decimal (ge=0) = 0,
  stock_minimo: Decimal (ge=0) = 0, costo_unitario: Decimal (ge=0) = 0 }`.
- `InsumoUpdate`: `{ nombre_insumo?: str, descripcion?: str, stock_minimo?: Decimal (ge=0),
  costo_unitario?: Decimal (ge=0) }` (no incluye `stock_actual`).
- `InsumoOut`: `{ id_insumo, nombre_insumo, id_unidad, unidad: UnidadOut, descripcion,
  stock_actual, stock_minimo, costo_unitario }`.
- `MovimientoCreate`: `{ tipo: str, motivo: str, cantidad: Decimal (gt=0) }`.

## Servicio (`services/insumo_service.py`)

- `_check_rol(usuario)` — Cocinero/Admin, si no → 403. `_ROLES_INV = {"Cocinero", "Administrador"}`.
- `listar_unidades(db) -> list[UnidadMedida]`.
- `listar(db, usuario) -> list[Insumo]` (ordenado por nombre).
- `get_or_404(db, id_insumo) -> Insumo`.
- `crear(db, data: InsumoCreate, usuario) -> Insumo` — valida rol y `id_unidad` (422).
- `actualizar(db, id_insumo, data: InsumoUpdate, usuario) -> Insumo`.
- `registrar_movimiento(db, id_insumo, data: MovimientoCreate, usuario) -> Insumo` — reglas
  de arriba.

`_TIPOS = {"Entrada", "Salida"}`, `_MOTIVOS_MANUAL = {"Ajuste", "Merma"}`.
Relación ORM: `Insumo.unidad = relationship("UnidadMedida")`.

## Componentes

```
backend/app/
├── models/inventario.py        # + relación Insumo.unidad
├── schemas/insumo.py           # UnidadOut, InsumoCreate/Update/Out, MovimientoCreate (nuevo)
├── services/insumo_service.py  # listar_unidades, listar, get_or_404, crear, actualizar, registrar_movimiento (nuevo)
└── api/v1/insumos.py           # /unidades, /insumos..., /insumos/{id}/movimientos (nuevo; en router.py)

mobile/src/
├── api/client.ts               # tipo Insumo; getInsumos, getInsumo, registrarMovimiento
├── lib/inventario.ts           # stockBajo, movimientoValido (nuevo)
├── app/cocina/inventario.tsx   # lista con alertas (nuevo)
├── app/cocina/ajuste.tsx       # formulario de movimiento (nuevo)
├── app/cocina/index.tsx        # + enlace "Inventario" en el header
└── app/_layout.tsx             # registrar cocina/inventario y cocina/ajuste
```

## Móvil

### Navegación

- Enlace "Inventario" en el header de `cocina/index.tsx` → `router.push("/cocina/inventario")`.
- `_layout.tsx`: registrar `<Stack.Screen name="cocina/inventario" />` y
  `<Stack.Screen name="cocina/ajuste" />`.

### `cocina/inventario.tsx`

- Al enfocar: `getInsumos`. Lista: `nombre_insumo`, `stock_actual` `abreviatura` /
  mínimo; **resaltado si `stockBajo(insumo)`** (`stock_actual ≤ stock_minimo`).
- Tocar un insumo → `router.push("/cocina/ajuste?id_insumo=X")`.
- Header con enlace "‹ Cocina". Errores de carga → "tocar para reintentar".

### `cocina/ajuste.tsx`

- Trae el insumo (`getInsumo`); muestra stock actual.
- Formulario: **tipo** (Entrada/Salida, chips), **motivo** (Ajuste/Merma, chips),
  **cantidad** (`TextInput` numérico). "Registrar" habilitado con `movimientoValido(...)`.
- Al enviar: `registrarMovimiento(id, { tipo, motivo, cantidad })` → muestra el insumo
  actualizado y permite volver a `/cocina/inventario`. 422 (salida > stock) → `Alert`.

### Cliente API (`api/client.ts`)

- `Insumo = { id_insumo, nombre_insumo, id_unidad, unidad: { nombre_unidad, abreviatura },
  descripcion: string | null, stock_actual: number, stock_minimo: number,
  costo_unitario: number }`.
- `getInsumos(access): Promise<Insumo[]>` → `GET /insumos`.
- `getInsumo(access, id): Promise<Insumo>` → `GET /insumos/{id}`.
- `registrarMovimiento(access, id, data: { tipo: string; motivo: string; cantidad: number }): Promise<Insumo>`
  → `POST /insumos/{id}/movimientos`.

### Lógica pura (`lib/inventario.ts`)

- `stockBajo(insumo: { stock_actual: number; stock_minimo: number }): boolean` →
  `stock_actual <= stock_minimo`.
- `movimientoValido(tipo: string | null, motivo: string | null, cantidadTxt: string): boolean`
  → `tipo !== null && motivo !== null && Number(cantidadTxt) > 0`.

## Manejo de errores

| Situación | Backend | Móvil |
|---|---|---|
| Sin token | 401 | — |
| Rol ≠ Cocinero/Admin | 403 | — |
| Insumo inexistente | 404 | — |
| Unidad inexistente / `cantidad ≤ 0` / `tipo`/`motivo` inválido | 422 | botón deshabilitado |
| Salida > stock | 422 | `Alert` |
| Fallo de carga / registro | — | "reintentar" / `Alert` |

## Testing

### Backend (`pytest`)

- `GET /unidades` → 5, exige token.
- `GET /insumos` → rol Cocinero 200; rol Mesero 403.
- `POST /insumos` (Cocinero) → 201 con `unidad.abreviatura`; unidad inexistente → 422.
- Movimiento **Entrada** suma al `stock_actual`; **Salida** resta.
- Salida mayor al stock → 422; `cantidad` 0 → 422; `tipo` inválido → 422; rol Mesero → 403.

### Móvil (`jest` + `tsc`)

- Cliente: `getInsumos`/`getInsumo` (bearer + URL); `registrarMovimiento("tok", 3, {...})`
  hace `POST /insumos/3/movimientos` con el cuerpo y bearer.
- Lógica: `stockBajo({stock_actual:2, stock_minimo:5})=true`,
  `stockBajo({stock_actual:9, stock_minimo:5})=false`; `movimientoValido("Salida","Merma","2")=true`,
  y falsos con tipo/motivo null o cantidad ≤ 0.
- `tsc --noEmit` limpio.

## Fuera de alcance (YAGNI)

Recetas y descuento automático (slice 2), compras (slice 3), borrar insumos, kárdex visible
(historial de movimientos), crear insumos desde el móvil, reportes (Sprint 6).
