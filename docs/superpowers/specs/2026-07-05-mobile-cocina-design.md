# Diseño — Móvil Cocina: lista de pedidos activos y avance de estado (feature/mobile-cocina)

**Fecha:** 2026-07-05
**Sprint:** 3 (slice 2 de 3: móvil Cocina)
**Rama:** `feature/mobile-cocina`

## Objetivo

Pantalla de Cocina (rol Cocinero) que lista los pedidos activos
(Pendiente + En preparación) y permite avanzar su estado, refrescándose por
*polling*. Consume la API de transiciones del slice 1. Segundo slice del Sprint 3;
el tercero es el móvil Mesero en vivo.

Cubre la parte de Cocina de RF-M18..M26.

## Decisiones tomadas (brainstorming)

1. **Contenido:** solo pedidos activos (Pendiente + En preparación). Al marcar
   "Listo", el pedido desaparece de la lista (ya salió de cocina).
2. **Filtrado:** pequeño ajuste de backend — el `GET /pedidos` acepta `?estados=1,2`
   (CSV de ids) para traer varios estados en una llamada.
3. **Traducción nombre→id:** se añade `GET /estados` (catálogo) porque el
   `PATCH /pedidos/{id}/estado` (slice 1) exige el id del estado destino y el móvil
   solo conoce nombres.
4. **Polling** cada 10 s mientras la pantalla está enfocada.

## Backend (2 adiciones)

### 1. `GET /pedidos?estados=1,2`

- `pedido_service.list_pedidos` pasa a aceptar `estados: list[int] | None` y filtra
  con `Pedido.id_estado.in_(estados)`.
- El endpoint `GET /pedidos` añade el parámetro `estados: str | None` (CSV). Si viene,
  se parsea a `list[int]` y gana sobre `id_estado`. Se conserva `id_estado: int | None`
  por compatibilidad; el mesero sigue usando `mias`.
- Resolución en el endpoint:
  `ids = _parse_csv(estados) if estados else ([id_estado] if id_estado is not None else None)`.
  `_parse_csv("1,2") -> [1, 2]`.

### 2. `GET /estados`

- Nuevo router `api/v1/estados.py`, autenticado (`get_current_user`), solo lectura.
- Devuelve los 5 estados sembrados. Mismo patrón que `/mesas`, `/categorias`.
- Schema `EstadoOut`: `{ id_estado: int, nombre_estado: str }`.

## Móvil

### Rutas / navegación

- Nueva pantalla `mobile/src/app/cocina/index.tsx` (hoy `modulo/cocina` cae en el
  placeholder genérico `modulo/[key].tsx`).
- `lib/modules.ts`: `COCINA.ruta` de `/modulo/cocina` → `/cocina`.
- `_layout.tsx`: registrar `<Stack.Screen name="cocina/index" />`.

### Cliente API (`api/client.ts`)

- Extender el type `Pedido` para incluir lo que ya devuelve `PedidoOut`:
  `mesa: { numero_mesa }`, `estado: { id_estado, nombre_estado }`, `fecha_pedido`,
  `detalle: { cantidad, producto: { nombre_producto }, observaciones }[]`,
  `observaciones`.
- `getEstados(access): Promise<Estado[]>` → `GET /estados`.
- `getPedidos(access, opts?: { estados?: number[] }): Promise<Pedido[]>` → `GET /pedidos`
  con `params.estados = ids.join(",")` cuando se pasan.
- `cambiarEstadoPedido(access, id, id_estado): Promise<Pedido>` →
  `PATCH /pedidos/{id}/estado` con cuerpo `{ id_estado }`.

### Lógica pura (`lib/cocina.ts`)

- `minutosDesde(fechaISO: string, ahora?: Date): number` — minutos enteros
  transcurridos.
- `accionCocina(nombreEstado: string): { label: string; destinoNombre: string } | null`
  - `Pendiente` → `{ label: "Iniciar preparación", destinoNombre: "En preparación" }`
  - `En preparación` → `{ label: "Marcar listo", destinoNombre: "Listo" }`
  - otro → `null`

### Pantalla `cocina/index.tsx` (data flow)

1. Al enfocar (`useFocusEffect`): `getEstados` una vez (mapa nombre→id) +
   `getPedidos({ estados: [idPendiente, idEnPreparación] })`.
2. **Polling:** `setInterval` cada 10 s mientras enfocada; se limpia al salir
   (retorno del `useFocusEffect`). Recargas silenciosas: spinner solo en la carga
   inicial, no en refrescos.
3. Ordena por `fecha_pedido` ascendente (lo más viejo primero).
4. **Tarjeta:** `Mesa N · #id_pedido · hace X min`, badge de estado, líneas
   (`cantidad × producto`), observaciones si hay. Botón de acción según
   `accionCocina(estado)`; la pantalla resuelve `destinoNombre`→id con el mapa de
   estados y llama `cambiarEstadoPedido`.
5. Tras PATCH exitoso: **refetch** de la lista (el pedido que pasa a Listo desaparece
   solo). Si el PATCH falla (p. ej. 409 por estado desincronizado): `Alert` + refetch.
6. Header con "Salir" (logout) como en las pantallas de Mesero.

## Componentes

```
backend/app/
├── schemas/estado.py            # EstadoOut (nuevo)
├── api/v1/estados.py            # GET /estados (nuevo; registrar en router.py)
├── services/pedido_service.py   # list_pedidos acepta estados: list[int] | None
└── api/v1/pedidos.py            # GET soporta ?estados=1,2 (CSV) + _parse_csv

mobile/src/
├── api/client.ts                # getEstados, getPedidos, cambiarEstadoPedido; type Pedido/Estado
├── lib/cocina.ts                # minutosDesde, accionCocina (lógica pura)
├── app/cocina/index.tsx         # pantalla (nueva)
├── app/_layout.tsx              # registrar "cocina/index"
└── lib/modules.ts               # COCINA.ruta -> "/cocina"
```

## Manejo de errores

| Situación | Comportamiento |
|---|---|
| Fallo al cargar la lista | Mensaje con "tocar para reintentar" (patrón de `mesas.tsx`) |
| PATCH 409 (estado desincronizado) | `Alert` + refetch (otro dispositivo ya avanzó el pedido) |
| PATCH otro error | `Alert` genérico + refetch |
| Sin token en los GET/PATCH | 401 (no debería ocurrir si hay sesión) |

## Testing

### Backend (`pytest` en el contenedor)

- `GET /estados` devuelve los 5 estados y exige token (401 sin él).
- `GET /pedidos?estados=1,2` trae solo pedidos en esos estados; `?id_estado=` sigue
  funcionando (compat).

### Móvil (`jest` + `tsc`)

- Cliente: `getEstados` pega a `/estados` con bearer; `getPedidos({estados:[1,2]})`
  manda `params.estados = "1,2"` y bearer; `cambiarEstadoPedido` hace
  `PATCH /pedidos/{id}/estado` con `{ id_estado }` y bearer.
- Lógica: `minutosDesde` con una fecha conocida; `accionCocina` para Pendiente,
  En preparación, Listo (null) y desconocido (null).
- `tsc` limpio.

## Fuera de alcance (YAGNI)

Notificación/estado en vivo para el mesero (slice 3), cancelar desde cocina
(el Cocinero no puede — slice 1), sonidos/push, edición de pedidos, sección de
"Listos" recientes, refresh-on-401 global.
