# Diseño — Móvil Mesero en vivo: Mis pedidos, estado y entrega (feature/mobile-mesero-vivo)

**Fecha:** 2026-07-05
**Sprint:** 3 (slice 3 de 3: móvil Mesero en vivo)
**Rama:** `feature/mobile-mesero-vivo`

## Objetivo

Dar al Mesero visibilidad en vivo de sus pedidos y la acción de entrega. Pantalla
"Mis pedidos" que lista los pedidos activos del mesero (Pendiente / En preparación /
Listo), se refresca por *polling* y permite marcar Entregado los que están Listo.
Cierra el Sprint 3.

Cubre la parte de Mesero de RF-M18..M26.

## Decisiones tomadas (brainstorming)

1. **Navegación:** enlace "Mis pedidos" desde la pantalla de Mesas (stack plano; el
   Mesero sigue aterrizando en `/mesero/mesas`).
2. **Contenido:** solo pedidos activos del mesero (Pendiente / En preparación / Listo);
   al entregar, el pedido desaparece de la lista.
3. **Cancelación:** fuera de alcance en este slice (aunque el backend la soporte).
4. **Sin cambios de backend:** el `GET /pedidos` ya combina `?mias=true` + `?estados=`
   (ambos filtros aplican) y el `PATCH /pedidos/{id}/estado` ya permite al Mesero
   Listo→Entregado (slice 1). Solo se añade una prueba que fija el comportamiento.

## Navegación

- `mesero/mesas.tsx`: botón "Mis pedidos" en el header → `router.push("/mesero/mis-pedidos")`.
- `mesero/mis-pedidos.tsx`: header con enlace de vuelta a Mesas y "Salir" (logout).
- `_layout.tsx`: registrar `<Stack.Screen name="mesero/mis-pedidos" />`.
- `modules.ts` no cambia (el Mesero sigue aterrizando en `/mesero/mesas`).

## Pantalla `mesero/mis-pedidos.tsx` (data flow)

1. Al enfocar (`useFocusEffect`): `getEstados` una vez (mapa nombre→id, reusado del
   slice 2) + `getPedidos({ mias: true, estados: [idPendiente, idEnPreparación, idListo] })`.
2. **Polling:** `setInterval` cada 10 s mientras enfocada; se limpia al salir. Recargas
   silenciosas (spinner solo en la carga inicial). Esto materializa la "notificación de
   listo": cuando Cocina marca Listo, aparece en vivo aquí.
3. **Orden:** por `prioridadEstado` (Listo primero) y, a igualdad, por `fecha_pedido`
   ascendente.
4. **Tarjeta:** `Mesa N · #id_pedido · hace X min` (reusa `minutosDesde` del slice 2),
   badge de estado y líneas (`cantidad × producto`). Si el estado es `Listo`: resaltado
   "¡Listo para entregar!" y botón **"Marcar entregado"** que llama
   `cambiarEstadoPedido(id, idEntregado)`. Pendiente / En preparación: sin botón
   (esperando a cocina).
5. Tras entregar con éxito: **refetch** (el pedido pasa a Entregado y sale de la lista).
   Si el PATCH falla: `Alert` + refetch. La mesa **permanece Ocupada** (se libera en el
   cobro, Sprint 4).

## Cliente API (`api/client.ts`)

- Extender `getPedidos` para aceptar también `mias`:
  `getPedidos(access, opts?: { estados?: number[]; mias?: boolean }): Promise<Pedido[]>`.
  Construye `params` con `estados` (CSV) y/o `mias: true`. Retrocompatible: la llamada de
  Cocina (`{ estados }`) no cambia.
- Se reutilizan `getEstados` y `cambiarEstadoPedido` del slice 2 sin cambios.

## Lógica pura (`lib/mesero.ts`)

- `entregable(nombreEstado: string): boolean` → `nombreEstado === "Listo"`.
- `prioridadEstado(nombreEstado: string): number` → `Listo` = 0, `En preparación` = 1,
  `Pendiente` = 2, otro = 3 (para ordenar Listo primero).

## Componentes

```
mobile/src/
├── api/client.ts               # getPedidos acepta { mias?: boolean }
├── lib/mesero.ts               # entregable, prioridadEstado (nuevo)
├── app/mesero/mis-pedidos.tsx  # pantalla (nueva)
├── app/mesero/mesas.tsx        # + enlace "Mis pedidos" en el header
└── app/_layout.tsx             # registrar "mesero/mis-pedidos"

backend/tests/test_pedidos_api.py  # + test mias+estados (sin cambio de código)
```

## Manejo de errores

| Situación | Comportamiento |
|---|---|
| Fallo al cargar la lista | Mensaje con "tocar para reintentar" (patrón de `mesas.tsx`) |
| PATCH al entregar falla (p. ej. 409) | `Alert` + refetch |
| Sin token | 401 (no debería ocurrir con sesión activa) |

## Testing

### Backend (`pytest` en el contenedor)

- `GET /pedidos?mias=true&estados=<Pendiente>,<Listo>` devuelve solo los pedidos activos
  del usuario actual: incluye el propio Pendiente/Listo, excluye el de otro usuario y
  excluye un Entregado propio.

### Móvil (`jest` + `tsc`)

- Cliente: `getPedidos("tok", { mias: true, estados: [1, 2, 3] })` manda
  `params = { estados: "1,2,3", mias: true }` y bearer.
- Lógica: `entregable("Listo")` true y otros false; `prioridadEstado` ordena
  Listo < En preparación < Pendiente < desconocido.
- `tsc --noEmit` limpio.

## Fuera de alcance (YAGNI)

Cancelar desde el móvil, sección de Entregados recientes, liberar la mesa al entregar
(es en el cobro, Sprint 4), notificaciones push reales, edición de pedidos.
