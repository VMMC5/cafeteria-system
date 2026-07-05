# Diseño — Gastos: registro de egresos (API + móvil) (feature/gastos)

**Fecha:** 2026-07-05
**Sprint:** 4 (slice 3 de 3: gastos)
**Rama:** `feature/gastos`

## Objetivo

Registrar y consultar egresos generales (gastos) desde la Caja. API para crear/listar
gastos y su catálogo de categorías, y una pantalla móvil con formulario + lista de
recientes. Cierra el Sprint 4.

Cubre RF de gastos.

## Contexto

El esquema ya existe (Sprint 0): `gastos` (`id_gasto`, `id_usuario`, `id_categoria_gasto`,
`concepto`, `monto`, `fecha_gasto`) y `categorias_gasto` (sembrado: Servicios, Nómina,
Mantenimiento). No hay migración.

## Decisiones tomadas (brainstorming)

1. **Autorización:** registrar y listar gastos → **Cajero / Administrador** (guard por rol
   dentro del servicio, como el cobro). El catálogo de categorías es de solo lectura para
   cualquier autenticado.
2. **Móvil:** formulario de registro + lista de gastos recientes.

## API (`/api/v1`)

| Método | Ruta | Descripción | Autorización |
|---|---|---|---|
| GET | `/gastos/categorias` | Catálogo de categorías de gasto | autenticado |
| POST | `/gastos` | Registra un gasto | Cajero / Admin |
| GET | `/gastos` | Gastos recientes (orden desc. por fecha) | Cajero / Admin |

### Reglas de `POST /gastos`

Entrada (`GastoCreate`): `{ id_categoria_gasto, concepto, monto }`.
1. Rol ∈ {Cajero, Administrador}; si no → **403**.
2. `concepto` no vacío y `monto > 0` (**422** vía schema).
3. `id_categoria_gasto` debe existir → **422** si no.
4. Se crea el `Gasto` con `id_usuario` = usuario actual y `fecha_gasto` por defecto.

## Schemas (`schemas/gasto.py`)

- `CategoriaGastoOut`: `{ id_categoria_gasto, nombre_categoria }`.
- `GastoCreate`: `{ id_categoria_gasto: int, concepto: str (min_length=1),
  monto: Decimal (gt=0) }`.
- `GastoOut`: `{ id_gasto, id_categoria_gasto, categoria: {nombre_categoria}, concepto,
  monto, fecha_gasto, id_usuario }`.

## Servicio (`services/gasto_service.py`)

- `listar_categorias(db) -> list[CategoriaGasto]`.
- `crear(db, data: GastoCreate, usuario) -> Gasto` — valida rol (403) y categoría (422);
  crea el gasto con `id_usuario` del actual; commit.
- `listar(db, usuario) -> list[Gasto]` — valida rol (403); gastos ordenados desc. por
  `id_gasto`.

Relación ORM: `Gasto.categoria = relationship("CategoriaGasto")` (para `GastoOut`).
El rol se lee de `usuario.rol.nombre_rol` (patrón del cobro); `_ROLES_GASTO = {"Cajero", "Administrador"}`.

## Componentes

```
backend/app/
├── models/gasto.py           # + relación Gasto.categoria
├── schemas/gasto.py          # CategoriaGastoOut, GastoCreate, GastoOut (nuevo)
├── services/gasto_service.py # listar_categorias, crear, listar (+ guard por rol) (nuevo)
└── api/v1/gastos.py          # GET /gastos/categorias, POST /gastos, GET /gastos (nuevo; en router.py)

mobile/src/
├── api/client.ts             # tipos Gasto/CategoriaGasto; getCategoriasGasto, getGastos, crearGasto
├── lib/gastos.ts             # gastoValido (nuevo)
├── app/caja/gastos.tsx       # formulario + lista (nuevo)
├── app/caja/index.tsx        # + enlace "Gastos" en el header
└── app/_layout.tsx           # registrar caja/gastos
```

## Móvil

### Navegación

- Enlace "Gastos" en el header de `caja/index.tsx` → `router.push("/caja/gastos")`.
- `_layout.tsx`: registrar `<Stack.Screen name="caja/gastos" />`.

### Pantalla `caja/gastos.tsx`

- **Formulario:** categoría (chips desde `getCategoriasGasto`), concepto (`TextInput`),
  monto (`TextInput` numérico). "Registrar" habilitado cuando `gastoValido(...)`.
- Al registrar: `crearGasto(...)` → limpia el formulario y recarga la lista.
- **Lista de recientes** (`getGastos`): concepto, categoría, monto, fecha.
- Errores: fallo de carga → "tocar para reintentar"; fallo al registrar → `Alert`.

### Cliente API (`api/client.ts`)

- `CategoriaGasto = { id_categoria_gasto: number; nombre_categoria: string }`.
- `Gasto = { id_gasto, id_categoria_gasto, categoria: { nombre_categoria }, concepto,
  monto: number, fecha_gasto: string, id_usuario }`.
- `getCategoriasGasto(access): Promise<CategoriaGasto[]>` → `GET /gastos/categorias`.
- `getGastos(access): Promise<Gasto[]>` → `GET /gastos`.
- `crearGasto(access, data: { id_categoria_gasto: number; concepto: string; monto: number }): Promise<Gasto>`
  → `POST /gastos`.

### Lógica pura (`lib/gastos.ts`)

- `gastoValido(categoriaId: number | null, concepto: string, montoTxt: string): boolean`
  → `categoriaId !== null && concepto.trim() !== "" && Number(montoTxt) > 0`.

## Manejo de errores

| Situación | Backend | Móvil |
|---|---|---|
| Sin token | 401 | — |
| Rol ≠ Cajero/Admin | 403 | — |
| Categoría inexistente | 422 | — |
| `monto ≤ 0` / `concepto` vacío | 422 | botón deshabilitado (`gastoValido`) |
| Fallo de carga / registro | — | "reintentar" / `Alert` |

## Testing

### Backend (`pytest`)

- `GET /gastos/categorias` → 3 categorías, exige token.
- `POST /gastos` (Cajero) → 201; `categoria.nombre_categoria` presente; aparece en `GET /gastos`.
- Rol Mesero → 403; `monto` 0 → 422; `concepto` vacío → 422; categoría inexistente → 422.

### Móvil (`jest` + `tsc`)

- Cliente: `getCategoriasGasto`/`getGastos` (bearer + URL); `crearGasto("tok", {...})`
  hace `POST /gastos` con el cuerpo y bearer.
- Lógica: `gastoValido(1,"Luz","100")=true`; `gastoValido(null,"Luz","100")=false`;
  `gastoValido(1,"","100")=false`; `gastoValido(1,"Luz","0")=false`.
- `tsc --noEmit` limpio.

## Fuera de alcance (YAGNI)

Editar/borrar gastos, filtros por fecha/categoría (reportes, Sprint 6), adjuntar
comprobantes, gastos ligados a compras de insumos (Sprint 5).
