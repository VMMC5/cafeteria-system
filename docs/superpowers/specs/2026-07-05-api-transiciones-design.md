# Diseño — API de transiciones de estado del pedido (feature/api-transiciones)

**Fecha:** 2026-07-05
**Sprint:** 3 (slice 1 de 3: API de transiciones)
**Rama:** `feature/api-transiciones`

## Objetivo

Permitir avanzar un pedido por su ciclo de vida
(Pendiente → En preparación → Listo → Entregado) con validación de flujo y
autorización por rol, además de cancelarlo registrando el motivo. Primer slice del
Sprint 3; los siguientes son el móvil Cocina (slice 2) y el móvil Mesero en vivo
(slice 3), que consumen esta API vía polling sobre los GET ya existentes.

Cubre el backend de RF-M18..M26.

## Visión del Sprint 3 (contexto)

| Slice | Contenido | Estado |
|---|---|---|
| **1 — API transiciones** | Avance de estado + cancelación con autorización por rol | este spec |
| 2 — Móvil Cocina | Lista/filtro de pedidos, avanzar estado, polling | pendiente |
| 3 — Móvil Mesero en vivo | Estado en vivo, entregar, "Mis pedidos" | pendiente |

## Decisiones tomadas (brainstorming)

1. **Autorización por rol**, específica por transición (no un guard fijo en la ruta).
2. **Flujo lineal estricto** (solo avance +1); cualquier salto o retroceso → 409.
3. **Cancelación** con endpoint dedicado, motivo obligatorio, que libera la mesa.
4. **Entregado es terminal** en este slice; la mesa permanece Ocupada (cobro = Sprint 4).
5. **Sin migración**: los 5 estados y la tabla `Cancelacion` ya existen en BD.

## Reglas del flujo

Flujo lineal estricto (solo avance al siguiente estado inmediato).

| Transición | Roles permitidos |
|---|---|
| Pendiente → En preparación | Cocinero, Administrador |
| En preparación → Listo | Cocinero, Administrador |
| Listo → Entregado | Mesero, Administrador |

- Cualquier salto (p. ej. Pendiente → Listo) o retroceso → **409**.
- Avanzar un pedido en estado terminal (Entregado / Cancelado) → **409**.
- Transición válida pero rol no autorizado → **403**.

## Cancelación (camino alterno)

- Permitida en cualquier estado **excepto Entregado y Cancelado** (si no → 409).
- Roles: **Mesero, Administrador** (otro rol → 403).
- Efectos, en una sola transacción:
  1. Inserta fila en `Cancelacion` (`id_pedido`, `id_usuario` del actual, `motivo`, fecha por defecto).
  2. Estado del pedido → **Cancelado**.
  3. Mesa **Ocupada → Disponible**.

## Endpoints (`/api/v1`)

Convención: ambos requieren `deps.get_current_user`.

| Método | Ruta | Descripción |
|---|---|---|
| PATCH | `/pedidos/{id}/estado` | Cuerpo `{ "id_estado": <destino> }`. Valida siguiente-permitido + rol. |
| POST | `/pedidos/{id}/cancelar` | Cuerpo `{ "motivo": str }`. |

Ambos devuelven el `PedidoOut` actualizado. Los GET de listar/detalle ya existen
(Sprint 2, slice 2) y sirven para el polling del móvil — no se tocan.

## Modelo de transiciones

Mapa explícito en `pedido_service.py` como fuente única de verdad:

```python
# estado_origen -> (estado_destino permitido, {roles autorizados})
_FLUJO = {
    "Pendiente":      ("En preparación", {"Cocinero", "Administrador"}),
    "En preparación": ("Listo",          {"Cocinero", "Administrador"}),
    "Listo":          ("Entregado",      {"Mesero",   "Administrador"}),
}
_CANCELABLE_ROLES = {"Mesero", "Administrador"}
_TERMINALES = {"Entregado", "Cancelado"}
```

## Lógica (`pedido_service.py`)

Funciones nuevas (reusan `get_or_404` y un helper `_estado_por_nombre` /
`_estado_por_id`, siguiendo el patrón de `_estado_pendiente`):

- **`cambiar_estado(db, id_pedido, id_estado_destino, usuario)`**
  1. Carga el pedido (404 si no existe) y resuelve el nombre del estado destino.
  2. Busca la transición permitida desde el estado actual en `_FLUJO`; si el destino
     no coincide (salto, retroceso o estado terminal) → 409.
  3. Verifica que el rol del usuario esté en el set de la transición → 403 si no.
  4. Actualiza `id_estado`, commit, devuelve el pedido.
- **`cancelar(db, id_pedido, motivo, usuario)`**
  1. Carga el pedido (404). Si su estado está en `_TERMINALES` → 409.
  2. Verifica rol en `_CANCELABLE_ROLES` → 403 si no.
  3. Crea `Cancelacion`, estado → Cancelado, mesa → Disponible, commit, devuelve el pedido.

## Autorización

El nombre de rol se obtiene del `usuario` ya cargado por `get_current_user`
(consultando `Rol` como en `require_admin`, o vía relationship `Usuario.rol`).
La comprobación vive **dentro del service**, junto al mapa `_FLUJO`, porque el rol
permitido depende de la transición concreta. No se añade un `require_role` genérico.

## Schemas (`schemas/pedido.py`)

- `EstadoUpdate`: `{ id_estado: int }`
- `CancelacionCreate`: `{ motivo: str }` (`min_length=1`)

## Componentes

```
backend/app/
├── schemas/pedido.py           # + EstadoUpdate, CancelacionCreate
├── services/pedido_service.py  # + _FLUJO, _CANCELABLE_ROLES, cambiar_estado, cancelar, helpers de estado
└── api/v1/pedidos.py           # + PATCH /{id}/estado, POST /{id}/cancelar
```

Sin migración Alembic (estados y `Cancelacion` ya sembrados/existentes).

## Manejo de errores

| Situación | Código |
|---|---|
| Sin token | 401 |
| Rol no autorizado para la transición o la cancelación | 403 |
| Pedido inexistente | 404 |
| Transición no lineal (salto/retroceso) o avanzar/cancelar un estado terminal | 409 |
| `id_estado` o `motivo` ausente/ inválido | 422 |

## Testing (`pytest` en el contenedor, TDD)

Reutiliza `client`, `admin_headers`, `mesero_headers` y añade `cocinero_headers`.
Crea mesa/producto/pedido vía los endpoints de Sprint 2. Casos:

- **Camino feliz:** cocinero avanza Pendiente→En preparación→Listo; mesero
  Listo→Entregado (cada paso 200 y `estado.nombre_estado` correcto).
- **Rol equivocado:** mesero intenta Pendiente→En preparación → 403; cocinero intenta
  Listo→Entregado → 403.
- **No lineal:** Pendiente→Listo (salto) → 409; Listo→En preparación (retroceso) → 409;
  avanzar un pedido Entregado → 409.
- **Cancelar OK:** pedido Pendiente → cancelar con motivo → estado Cancelado, fila en
  `Cancelacion` con el motivo y el usuario, mesa vuelve a Disponible.
- **Cancelar inválido:** sin motivo → 422; cancelar un Entregado → 409; cocinero
  cancela → 403.
- **404** en pedido inexistente para ambos endpoints.

## Fuera de alcance (YAGNI)

Notificación push real (el móvil hará polling sobre los GET existentes — slices 2/3),
cobro y liberación de mesa por venta (Sprint 4), edición de líneas del pedido,
reactivar un pedido cancelado, historial/auditoría de cambios de estado.
