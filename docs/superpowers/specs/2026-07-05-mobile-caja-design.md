# Diseño — Móvil Caja: cobro de pedidos y comprobante (feature/mobile-caja)

**Fecha:** 2026-07-05
**Sprint:** 4 (slice 2 de 3: móvil Caja)
**Rama:** `feature/mobile-caja`

## Objetivo

Pantallas de Caja (rol Cajero) para cobrar pedidos: listar pendientes de cobro, elegir
método de pago e ingresar el monto recibido (con cambio), y ver el comprobante con el
desglose de IVA. Consume la API de cobro del slice 1. Segundo slice del Sprint 4; el
tercero son los gastos.

Cubre la parte de Caja de RF-C (cobro).

## Decisiones tomadas (brainstorming)

1. **UX de pago:** un solo método + monto recibido + cambio (el pago dividido, que la API
   soporta, queda para después — YAGNI).
2. **Desglose pre-cobro:** antes de cobrar se muestra solo el **total**; el subtotal/IVA
   aparecen en el **comprobante** (vienen de la venta, autoritativos). El móvil no duplica
   la tasa de IVA.
3. **Catálogo de métodos:** se añade `GET /metodos_pago` (como `GET /estados`) para que la
   Caja arme el pago con ids reales.
4. **Comprobante inline:** la pantalla de cobro cambia a vista "Comprobante" tras el éxito
   (no hay ruta separada; usa la respuesta de `POST /ventas`).

## Backend (1 adición)

### `GET /metodos_pago`

- Nuevo router `api/v1/metodos_pago.py`, autenticado (`get_current_user`), solo lectura.
- Devuelve los métodos sembrados (Efectivo, Tarjeta, Transferencia, Otro).
- `response_model=list[MetodoResumen]` reutilizando el schema del slice 1
  (`schemas/venta.MetodoResumen` = `{id_metodo_pago, nombre_metodo}`).

## Navegación

- `modules.ts`: `CAJA.ruta` de `/modulo/caja` → `/caja`.
- `_layout.tsx`: registrar `<Stack.Screen name="caja/index" />` y `<Stack.Screen name="caja/cobro" />`.
- El Cajero sigue siendo rol de un solo módulo (aterriza directo en `/caja`).

## Flujo (2 pantallas)

### `caja/index.tsx` — pendientes de cobro

1. Al enfocar + **polling 10 s** (patrón de Cocina): `getPedidos({ por_cobrar: true })`.
2. Lista tarjetas: `Mesa N · #id_pedido · $total`. Tocar → `router.push("/caja/cobro?id_pedido=X")`.
3. Header con "Salir" (logout). Recargas silenciosas (spinner solo en carga inicial).

### `caja/cobro.tsx` — cobro + comprobante inline

**Estado "cobro":**
1. Trae el pedido (`getPedido(id)`) → muestra mesa, líneas y **total**.
2. Carga `getMetodosPago()` → chips de método; el cajero elige **uno**.
3. Input numérico "monto recibido"; muestra **cambio** en vivo (`cambio(recibido, total)`).
4. "Confirmar cobro" habilitado si `puedeCobrar(recibido, total)`.
5. Al confirmar: `cobrarVenta(id_pedido, [{ id_metodo_pago, monto: recibido }])`.

**Estado "comprobante"** (tras éxito, con la `Venta` devuelta):
- Folio, **desglose subtotal / IVA / total**, método y monto, **cambio**.
- Botón "Terminar" → `router.replace("/caja")`.

## Cliente API (`api/client.ts`)

Tipos nuevos:
- `MetodoPago = { id_metodo_pago: number; nombre_metodo: string }`
- `PagoOut = { id_pago: number; id_metodo_pago: number; metodo: { nombre_metodo: string };
  monto: number; referencia: string | null }`
- `Venta = { id_venta, id_pedido, folio, estado_venta, fecha_venta, total, subtotal, iva,
  cambio, pagos: PagoOut[] }`

Funciones:
- `getMetodosPago(access): Promise<MetodoPago[]>` → `GET /metodos_pago`.
- `getPedidos` gana `por_cobrar?: boolean` (manda `por_cobrar=true`); retrocompatible con
  `{ estados, mias }`.
- `getPedido(access, id): Promise<Pedido>` → `GET /pedidos/{id}`.
- `cobrarVenta(access, id_pedido, pagos): Promise<Venta>` → `POST /ventas` con cuerpo
  `{ id_pedido, pagos }`, donde `pagos: { id_metodo_pago: number; monto: number }[]`.

## Lógica pura (`lib/caja.ts`)

- `cambio(recibido: number, total: number): number` → `Math.max(0, recibido − total)`.
- `puedeCobrar(recibido: number, total: number): boolean` → `total > 0 && recibido ≥ total`.

## Componentes

```
backend/app/
├── api/v1/metodos_pago.py   # GET /metodos_pago (nuevo; registrar en router.py)

mobile/src/
├── api/client.ts            # tipos Venta/PagoOut/MetodoPago; getMetodosPago, getPedido, cobrarVenta; getPedidos +por_cobrar
├── lib/caja.ts              # cambio, puedeCobrar (nuevo)
├── app/caja/index.tsx       # pendientes de cobro (polling) (nuevo)
├── app/caja/cobro.tsx       # cobro + comprobante inline (nuevo)
├── app/_layout.tsx          # registrar caja/index y caja/cobro
└── lib/modules.ts           # CAJA.ruta -> /caja
```

## Manejo de errores

| Situación | Comportamiento |
|---|---|
| Fallo al cargar pendientes / pedido / métodos | Mensaje "tocar para reintentar" |
| Cobro 409 (ya cobrado / cancelado) | `Alert` y volver a `/caja` |
| Cobro 422 (pago insuficiente) | `Alert` (no debería ocurrir: el botón se bloquea) |
| Sin token | 401 (no debería con sesión activa) |

## Testing

### Backend (`pytest`)

- `GET /metodos_pago` devuelve 4 métodos e incluye "Efectivo"; exige token (401 sin él).

### Móvil (`jest` + `tsc`)

- Cliente: `getMetodosPago` (bearer + `/metodos_pago`); `getPedidos({por_cobrar:true})`
  manda `params { por_cobrar: true }`; `cobrarVenta("tok", 7, [{id_metodo_pago:1, monto:200}])`
  hace `POST /ventas` con `{ id_pedido: 7, pagos: [...] }` y bearer.
- Lógica: `cambio(200,116)=84`, `cambio(100,116)=0`; `puedeCobrar(116,116)=true`,
  `puedeCobrar(100,116)=false`, `puedeCobrar(0,0)=false`.
- `tsc --noEmit` limpio.

## Fuera de alcance (YAGNI)

Pago dividido en UI, gastos (slice 3), reimpresión/compartir comprobante, historial de
ventas, descuentos/propinas, refresh-on-401 global.
