# Spec — Guard de mesa Ocupada en la API

**Fecha:** 2026-08-08 · **Estado:** aprobado en brainstorming

## Objetivo

Cerrar el hueco diferido del review del PR #21: el panel web impide cambiar el estado de una mesa Ocupada, pero esa regla vive **solo** en la capa web. Por Swagger, curl o el móvil se puede liberar una mesa que tiene un pedido activo, dejando el pedido abierto y la mesa marcada como libre — y permitiendo que se tome otro pedido sobre una mesa ya en uso. Este slice mueve la regla a la API, que es la fuente de verdad.

## Alcance

Solo `backend/`. El hardening CSRF del panel web (el otro pendiente del mismo review) es un slice aparte: distinto subsistema, distinta suite, distinto riesgo.

## Decisiones tomadas (brainstorming)

- **El guard se apoya en el pedido real, no en la bandera `mesa.estado`.** Se descartó calcar la regla de la web (rechazar cuando `mesa.estado == "Ocupada"`) porque `pedido_service.crear` exige `estado == "Disponible"`: un admin podría marcar una mesa como Ocupada a mano y quedaría **bloqueada de forma permanente** — no acepta pedidos y tampoco se puede cambiar de estado.
- **`Ocupada` pasa a ser estado del sistema.** Lo asigna `crear` pedido; lo quitan el cobro y la cancelación. La edición manual solo maneja `Disponible ⇄ Reservada`.
- **Se descartó** volver `estado` de solo lectura con acciones explícitas (reservar/liberar): cambia el contrato del endpoint, rompe el formulario del panel y es un slice bastante mayor.

## Definición de "pedido activo" (una sola vez)

La regla ya existe implícita en `venta_service.listar_por_cobrar`: pedido **no Cancelado** y **sin Venta asociada**. Se extrae a `pedido_service` como predicado reutilizable y `listar_por_cobrar` pasa a consumirlo, para no dejar dos definiciones que puedan divergir.

Nuevo en `pedido_service`:

- `condiciones_pedido_activo(db) -> tuple` — devuelve las condiciones SQLAlchemy `(Pedido.id_estado != <id de Cancelado>, Pedido.id_pedido.not_in(select(Venta.id_pedido)))`. Es la única definición de la regla.
- `tiene_pedido_activo(db, id_mesa) -> bool` — aplica esas condiciones más `Pedido.id_mesa == id_mesa` y responde si existe al menos una fila.

`venta_service.listar_por_cobrar` se reescribe para construir su `select` con `condiciones_pedido_activo(db)` en vez de repetir la regla. Su comportamiento y su orden (`id_pedido` descendente) no cambian.
- Sin ciclos de import: `pedido_service` importa modelos y `receta_service`; no importa `venta_service` ni `mesa_service`. `venta_service` y `mesa_service` sí pueden importar `pedido_service`.

## El guard — `mesa_service.update`

Se dispara **solo si el estado realmente cambia** (`data.estado is not None and data.estado != obj.estado`), para que un PUT que reenvía el mismo valor no falle sin motivo.

| Caso | Código | Mensaje |
|---|---|---|
| Destino `"Ocupada"` | **422** | El estado Ocupada lo asigna el sistema al crear un pedido |
| La mesa tiene un pedido activo | **409** | La mesa tiene un pedido activo; su estado lo gestiona el sistema |
| `Disponible ⇄ Reservada` | 200 | — |
| Mesa marcada `Ocupada` **sin** pedido activo | 200 | permite destrabar datos viejos o inconsistentes |

Orden de comprobación: primero el destino `"Ocupada"` (422), luego el pedido activo (409).

`numero_mesa`, `capacidad` y `ubicacion` **siguen editables** aunque la mesa tenga un pedido activo: el guard es exclusivamente sobre `estado`. La validación de unicidad de `numero_mesa` no cambia.

`delete` no se toca: ya rechaza 409 si la mesa tiene pedidos asociados.

## Efecto sobre la web

El panel **no cambia** en este slice. Sigue quitando `estado` del payload cuando la mesa está Ocupada y avisando con un flash; queda como conveniencia de UX y la API pasa a ser quien hace cumplir la regla.

Divergencia conocida y aceptada: la web mira la bandera `mesa.estado`, la API mira el pedido real. En el caso raro de una mesa marcada Ocupada sin pedido activo, la web seguirá bloqueando el cambio en el formulario aunque la API lo permita; destrabar esa mesa se hace por API. Queda anotado como deuda menor.

## Tests (`backend/tests/test_mesas_api.py`, TDD)

- Mesa con pedido activo, cambiar `estado` → **409**.
- Poner `estado = "Ocupada"` a mano en una mesa disponible → **422**.
- `Disponible → Reservada` en una mesa libre → **200**.
- Mesa marcada `Ocupada` sin pedido activo → **200** (destrabar).
- Reenviar el mismo `estado` en una mesa con pedido activo → **200** (no-op no falla).
- Cambiar `capacidad` en una mesa con pedido activo → **200** (el guard no toca otros campos).
- Tras cobrar el pedido, la mesa vuelve a ser editable → **200**.

## Fuera de alcance

- Hardening CSRF del panel web (slice aparte).
- Cambiar el contrato de `MesaUpdate` o añadir endpoints de reservar/liberar.
- Alinear la regla de la web con la de la API (hoy mira la bandera).
- Cualquier cambio en `pedido_service.crear` o en el flujo de cobro/cancelación.
