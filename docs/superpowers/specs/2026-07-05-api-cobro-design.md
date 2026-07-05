# Diseño — API de cobro: venta, IVA, pagos y cambio (feature/api-cobro)

**Fecha:** 2026-07-05
**Sprint:** 4 (slice 1 de 3: API de cobro)
**Rama:** `feature/api-cobro`

## Objetivo

Cobrar un pedido: registrar la venta 1:1, sus pagos (con pago dividido), desglosar el
IVA, calcular el cambio y liberar la mesa. Primer slice del Sprint 4 (hito crítico de
Caja); los siguientes son el móvil Caja (slice 2) y los gastos (slice 3).

Cubre el backend de RF-C (cobro/ventas).

## Visión del Sprint 4 (contexto)

| Slice | Contenido | Estado |
|---|---|---|
| **1 — API cobro** | Venta + IVA + pagos + cambio + ticket + libera mesa | este spec |
| 2 — Móvil Caja | Pendientes de cobro → detalle con impuestos → pago → comprobante | pendiente |
| 3 — Gastos | API + móvil de egresos | pendiente |

El esquema ya existe (migración Sprint 0): `ventas` (1:1 pedido), `tickets` (folio),
`pagos` (1:N, soporta pago dividido), `metodos_pago` (Efectivo/Tarjeta/Transferencia/Otro,
sembrados), `configuracion` (clave-valor). No hay migración nueva.

## Decisiones tomadas (brainstorming)

1. **Cobrable:** pedido **no Cancelado** y **sin venta previa** (venta 1:1). El cobro es
   independiente del flujo de cocina y **libera la mesa**.
2. **IVA incluido/desglosado:** `Venta.total = total del pedido`. Se desglosa para el
   comprobante: `base = round(total/(1+tasa), 2)`, `iva = total − base`. Tasa 16% en
   `configuracion` (clave `iva_tasa`).
3. **Pagos y cambio:** `pagos: [{id_metodo_pago, monto}]`; se valida `Σ montos ≥ total`
   (si no → 422); `cambio = Σ montos − total` (derivado, no se persiste). Los pagos se
   guardan tal cual.
4. **Autorización:** cobrar solo **Cajero / Administrador** (403 si no), rol leído dentro
   del servicio (patrón del slice 1 del Sprint 3).

## Endpoints (`/api/v1`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/pedidos?por_cobrar=true` | Pendientes de cobro (no Cancelado, sin venta), con detalle y total |
| POST | `/ventas` | `{ id_pedido, pagos: [{id_metodo_pago, monto, referencia?}] }` → crea venta+pagos+ticket, libera mesa. 201 con desglose |
| GET | `/ventas/{id}` | Detalle de la venta para el comprobante |

Todos requieren `deps.get_current_user`.

## Cobrar — lógica (`venta_service.cobrar`)

Entrada (`VentaCreate`):
```json
{
  "id_pedido": 7,
  "pagos": [
    {"id_metodo_pago": 1, "monto": 200.00, "referencia": null}
  ]
}
```

Pasos y reglas (una transacción):
1. Rol del usuario ∈ {Cajero, Administrador}; si no → **403**.
2. El pedido debe existir (**404**).
3. El pedido no puede estar **Cancelado** (**409**).
4. El pedido no puede tener ya una venta (**409** "ya cobrado").
5. `pagos` no vacío (≥ 1) y cada `monto > 0` (**422** vía schema); cada `id_metodo_pago`
   debe existir (**422**).
6. `total = pedido.total` (Σ subtotales). `Σ montos ≥ total`, si no → **422**.
7. Crea `Venta(id_pedido, id_usuario=usuario, total, estado_venta="Completada")` y hace
   flush para obtener `id_venta`.
8. Crea los `Pago` (método, monto, referencia).
9. Crea `Ticket` con `folio = "V-" + str(id_venta).zfill(6)`.
10. Libera la mesa del pedido (**Ocupada → Disponible**).
11. Commit; devuelve la venta.

## Desglose y cambio

- `_iva_tasa(db) -> Decimal`: lee `configuracion.iva_tasa`; default `Decimal("0.16")` si
  faltara la fila.
- `desglose(total, tasa) -> (base, iva)` (pura): `base = round(total/(1+tasa), 2)`,
  `iva = total − base`.
- `cambio = Σ pagos.monto − total` (derivado en `to_out`).

## Relaciones ORM añadidas (sin migración)

- `Venta.pagos = relationship("Pago")` (1:N)
- `Venta.ticket = relationship("Ticket", uselist=False)`
- `Pago.metodo = relationship("MetodoPago")`
- Consulta de venta por `id_pedido` para detectar "ya cobrado" y filtrar por-cobrar.

## Schemas (`schemas/venta.py`)

- `PagoIn`: `{ id_metodo_pago: int, monto: Decimal (gt=0), referencia: str | None = None }`.
- `VentaCreate`: `{ id_pedido: int, pagos: list[PagoIn] (min_length=1) }`.
- `MetodoResumen`: `{ id_metodo_pago, nombre_metodo }`.
- `PagoOut`: `{ id_pago, id_metodo_pago, metodo: MetodoResumen, monto, referencia }`.
- `VentaOut`: `{ id_venta, id_pedido, fecha_venta, estado_venta, folio, total, subtotal,
  iva, cambio, pagos: [PagoOut] }` — `subtotal`/`iva`/`cambio` son derivados (no columnas).

`to_out(venta, tasa) -> VentaOut` arma `subtotal`/`iva` (vía `desglose`), `cambio` y `folio`
(de `venta.ticket.folio`).

## Componentes

```
backend/app/
├── models/venta.py             # + relaciones Venta.pagos/ticket, Pago.metodo
├── schemas/venta.py            # PagoIn, VentaCreate, PagoOut, MetodoResumen, VentaOut (nuevo)
├── services/venta_service.py   # cobrar, listar_por_cobrar, get_or_404, _iva_tasa, desglose, to_out (nuevo)
├── api/v1/ventas.py            # POST /ventas, GET /ventas/{id} (nuevo; registrar en router.py)
├── api/v1/pedidos.py           # GET soporta ?por_cobrar=true
└── db/seed.py                  # + configuracion iva_tasa=0.16
```

## Manejo de errores

| Situación | Código |
|---|---|
| Sin token | 401 |
| Rol distinto de Cajero/Administrador | 403 |
| Pedido inexistente / Venta inexistente (GET) | 404 |
| Pedido Cancelado | 409 |
| Pedido ya tiene venta | 409 |
| `pagos` vacío, `monto ≤ 0`, método inexistente, o Σ montos < total | 422 |

## Testing (`pytest` en el contenedor)

Reutiliza `client`, `admin_headers`, `mesero_headers`, `cocinero_headers`; añade
`cajero`/`cajero_headers`. Helpers para crear mesa/producto/pedido (como en tests previos).

- `desglose(Decimal("116"), Decimal("0.16"))` → `(Decimal("100.00"), Decimal("16.00"))`.
- Cobrar OK → 201; `total` = total del pedido; `subtotal`/`iva` correctos; `folio` presente;
  mesa vuelve a **Disponible**; existe la venta 1:1.
- Pago dividido (Efectivo + Tarjeta) suma exacta → `cambio` = 0.00; sobrepago en efectivo →
  `cambio` correcto.
- Σ pagos < total → 422; `id_metodo_pago` inexistente → 422; `pagos` vacío → 422; `monto` 0 → 422.
- Cobrar pedido Cancelado → 409; cobrar dos veces el mismo pedido → 409.
- Rol Mesero intenta cobrar → 403.
- `GET /pedidos?por_cobrar=true` incluye un pedido activo sin venta; excluye uno Cancelado
  y uno ya cobrado.
- `GET /ventas/{id}` trae desglose y pagos; `GET /ventas/999999` → 404.

## Fuera de alcance (YAGNI)

Móvil Caja (slice 2), gastos (slice 3), reimpresión/anulación de ticket, devoluciones,
propinas, descuentos, listado/histórico de ventas, reportes (Sprint 6).
