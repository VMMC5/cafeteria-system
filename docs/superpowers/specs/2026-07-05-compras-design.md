# Diseño — Compras a proveedores (API + móvil) (feature/compras)

**Fecha:** 2026-07-05
**Sprint:** 5 (slice 3 de 3: compras)
**Rama:** `feature/compras`

## Objetivo

Registrar compras de insumos a proveedores: alta/listado de proveedores, y registro de una
compra multi-línea que da **entrada de stock** (kárdex) y actualiza el costo del insumo.
Cierra el Sprint 5.

Cubre RF de compras y entrada de inventario.

## Contexto

El esquema ya existe (Sprint 0): `proveedores`, `compras` (`id_proveedor`, `id_usuario`,
`total`, `folio_factura`), `detalle_compra` (`cantidad`, `costo_unitario`, `subtotal`
calculado por la BD) y `movimientos_inventario` (kárdex, `id_compra`, motivo `Compra`). No
hay migración. Slices previos: insumos (1) y recetas + descuento (2).

## Decisiones tomadas (brainstorming)

1. **Superficie:** API + móvil Cocina (pantalla para registrar compras).
2. **Costo del insumo:** al registrar una compra, `insumo.costo_unitario` se actualiza al
   **último costo de compra** (el de la línea).
3. **Autorización:** proveedores y compras → **Cocinero / Administrador**.

## Bloque 1 — API

| Método | Ruta | Descripción | Autorización |
|---|---|---|---|
| GET | `/proveedores` | Lista de proveedores | Cocinero / Admin |
| POST | `/proveedores` | Alta de proveedor | Cocinero / Admin |
| POST | `/compras` | Registrar compra (entrada de stock) | Cocinero / Admin |
| GET | `/compras` | Compras recientes (con detalle) | Cocinero / Admin |

### Alta de proveedor (`POST /proveedores`)

`ProveedorCreate`: `{ nombre_proveedor: str (min_length=1), telefono: str | None,
correo: str | None, direccion: str | None }`. Rol Cocinero/Admin → 403 si no.

### Registrar compra (`POST /compras`)

`CompraCreate`: `{ id_proveedor: int, folio_factura: str | None,
items: [{ id_insumo: int, cantidad: Decimal (gt=0), costo_unitario: Decimal (ge=0) }] (min_length=1) }`.

Pasos (una transacción):
1. Rol Cocinero/Admin → 403.
2. `id_proveedor` existe → 422 si no.
3. Cada `id_insumo` existe → 422 si no.
4. `total = Σ (cantidad × costo_unitario)`.
5. Crea `Compra(id_proveedor, id_usuario=actual, total, folio_factura)` y hace `flush`.
6. Por cada línea: crea `DetalleCompra(id_compra, id_insumo, cantidad, costo_unitario)`
   (el `subtotal` lo calcula la BD); `insumo.stock_actual += cantidad`;
   `insumo.costo_unitario = costo_unitario` (último costo); registra
   `MovimientoInventario(tipo_movimiento="Entrada", motivo="Compra", id_compra, id_insumo,
   id_usuario, cantidad)`.
7. Commit; devuelve la compra con su detalle y total.

### Seed

Se añaden **proveedores demo** (idempotente, por `nombre_proveedor`) para que el móvil
tenga de dónde elegir. Más proveedores se crean por API.

### Schemas (`schemas/compra.py`)

- `ProveedorCreate`: arriba. `ProveedorOut`: `{ id_proveedor, nombre_proveedor, telefono,
  correo, direccion }`.
- `CompraItemIn`: `{ id_insumo, cantidad (gt=0), costo_unitario (ge=0) }`.
- `CompraCreate`: `{ id_proveedor, folio_factura: str | None, items: [CompraItemIn] (min_length=1) }`.
- `InsumoResumen`: `{ id_insumo, nombre_insumo }`. `ProveedorResumen`: `{ id_proveedor, nombre_proveedor }`.
- `DetalleCompraOut`: `{ id_detalle_compra, id_insumo, insumo: InsumoResumen, cantidad,
  costo_unitario, subtotal }`.
- `CompraOut`: `{ id_compra, id_proveedor, proveedor: ProveedorResumen, fecha_compra, total,
  folio_factura, detalle: [DetalleCompraOut] }`.

### Servicio (`services/compra_service.py`)

- `_check_rol(usuario)` — Cocinero/Admin.
- `listar_proveedores(db, usuario) -> list[Proveedor]`; `crear_proveedor(db, data, usuario) -> Proveedor`.
- `crear_compra(db, data: CompraCreate, usuario) -> Compra` — pasos de arriba.
- `listar_compras(db, usuario) -> list[Compra]` (orden desc.).

Relaciones ORM: `Compra.proveedor`, `Compra.detalle` (1:N), `DetalleCompra.insumo`.

## Componentes

```
backend/app/
├── models/compra.py            # + relaciones Compra.proveedor/detalle, DetalleCompra.insumo
├── schemas/compra.py           # ProveedorCreate/Out, CompraItemIn, CompraCreate, DetalleCompraOut, CompraOut (nuevo)
├── services/compra_service.py  # proveedores + compra con entrada de stock (nuevo)
├── api/v1/proveedores.py       # GET/POST /proveedores (nuevo)
├── api/v1/compras.py           # POST/GET /compras (nuevo)  (ambos en router.py)
└── db/seed.py                  # + proveedores demo

mobile/src/
├── api/client.ts               # tipos Proveedor/Compra/DetalleCompra; getProveedores, getCompras, crearCompra
├── lib/compras.ts              # lineaCompraValida, compraTotal, compraValida (nuevo)
├── app/cocina/compras.tsx      # lista de compras recientes (nuevo)
├── app/cocina/compra-nueva.tsx # formulario multi-línea (nuevo)
├── app/cocina/index.tsx        # + enlace "Compras" en el header
└── app/_layout.tsx             # registrar cocina/compras y cocina/compra-nueva
```

## Móvil (Cocina)

### Navegación

- Enlace "Compras" en el header de `cocina/index.tsx` (junto a "Inventario") →
  `router.push("/cocina/compras")`.
- `_layout.tsx`: registrar `cocina/compras` y `cocina/compra-nueva`.

### `cocina/compras.tsx`

- Al enfocar: `getCompras`. Lista: proveedor, fecha (o folio) y `total`. Botón "Nueva
  compra" → `/cocina/compra-nueva`. Header "‹ Cocina". Errores → "reintentar".

### `cocina/compra-nueva.tsx`

- **Proveedor:** chips desde `getProveedores`.
- **Agregar línea:** insumo (chips desde `getInsumos`) + cantidad + costo unitario;
  "Agregar" valida con `lineaCompraValida` y mete la línea a una lista local con subtotal.
- Muestra las líneas agregadas y el **total** (`compraTotal`).
- Folio de factura (opcional, `TextInput`).
- **"Registrar compra"** habilitado con `compraValida` → `crearCompra(access,
  { id_proveedor, folio_factura, items })` → `router.replace("/cocina/compras")`.
  Error → `Alert`.

### Cliente API (`api/client.ts`)

- `Proveedor = { id_proveedor: number; nombre_proveedor: string }`.
- `DetalleCompra = { id_detalle_compra: number; id_insumo: number; insumo: { nombre_insumo: string };
  cantidad: number; costo_unitario: number; subtotal: number }`.
- `Compra = { id_compra, id_proveedor, proveedor: { nombre_proveedor }, fecha_compra: string,
  total: number, folio_factura: string | null, detalle: DetalleCompra[] }`.
- `getProveedores(access): Promise<Proveedor[]>` → `GET /proveedores`.
- `getCompras(access): Promise<Compra[]>` → `GET /compras`.
- `crearCompra(access, data: { id_proveedor: number; folio_factura: string | null;
  items: { id_insumo: number; cantidad: number; costo_unitario: number }[] }): Promise<Compra>`
  → `POST /compras`.

### Lógica pura (`lib/compras.ts`)

- `lineaCompraValida(idInsumo: number | null, cantidadTxt: string, costoTxt: string): boolean`
  → `idInsumo !== null && Number(cantidadTxt) > 0 && Number(costoTxt) >= 0 && costoTxt !== ""`.
- `compraTotal(lineas: { cantidad: number; costo_unitario: number }[]): number`
  → `Σ cantidad × costo_unitario`.
- `compraValida(idProveedor: number | null, lineas: unknown[]): boolean`
  → `idProveedor !== null && lineas.length > 0`.

## Manejo de errores

| Situación | Backend | Móvil |
|---|---|---|
| Sin token | 401 | — |
| Rol ≠ Cocinero/Admin | 403 | — |
| Proveedor / insumo inexistente | 422 | — |
| `items` vacío / `cantidad ≤ 0` | 422 | botones deshabilitados |
| Fallo de carga / registro | — | "reintentar" / `Alert` |

## Testing

### Backend (`pytest`)

- `GET /proveedores` (Cocinero 200, Mesero 403); `POST /proveedores` (Cocinero 201).
- `POST /compras` (2 líneas): 201; `total` = Σ subtotales; cada `insumo.stock_actual` sube
  la cantidad comprada; `insumo.costo_unitario` = costo de la línea; existe movimiento
  Entrada/Compra por línea con el `id_compra`.
- Proveedor inexistente → 422; insumo inexistente → 422; `items` vacío → 422; rol Mesero → 403.
- `GET /compras` lista la compra creada con su detalle.

### Móvil (`jest` + `tsc`)

- Cliente: `getProveedores`/`getCompras` (bearer + URL); `crearCompra("tok", {...})` hace
  `POST /compras` con el cuerpo y bearer.
- Lógica: `lineaCompraValida(1,"2","30")=true` y falsos (insumo null, cantidad 0, costo vacío);
  `compraTotal([{cantidad:2,costo_unitario:30},{cantidad:1,costo_unitario:10}])=70`;
  `compraValida(1,[{...}])=true`, `compraValida(null,[...])=false`, `compraValida(1,[])=false`.
- `tsc --noEmit` limpio.

## Fuera de alcance (YAGNI)

Editar/borrar compras y proveedores, devoluciones a proveedor, promedio ponderado de costo,
gestión de proveedores en móvil (solo se eligen), reportes (Sprint 6).
