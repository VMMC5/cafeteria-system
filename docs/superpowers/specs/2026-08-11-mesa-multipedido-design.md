# Varios pedidos por mesa — ordenar de nuevo sin cerrar la cuenta

**Fecha:** 2026-08-11 · **Alcance:** backend (reglas de mesa) + móvil (pantalla de Mesas). Web sin cambios.

## Problema

Hoy `POST /pedidos` exige mesa **Disponible** (409 si no), así que una mesa solo
puede tener un pedido activo. Si los clientes quieren ordenar algo más, el mesero
tiene que esperar a que caja cierre la cuenta (la mesa se libera) y abrir una
nueva — o meter los artículos extra por otra mesa. Operativamente absurdo: la
gente pide en rondas.

## Diseño

### Regla nueva de negocio

**Una mesa Ocupada acepta pedidos adicionales.** Cada ronda es un pedido
independiente que fluye igual que siempre (Pendiente → cocina → Listo →
Entregado → cobro), con su descuento de stock por receta y su propia cuenta.
La mesa se libera **solo al cerrar el último pedido activo**.

### Backend (3 cambios puntuales, `tiene_pedido_activo` ya existe del PR #24)

1. **`pedido_service.crear`**: acepta mesa `Disponible` u `Ocupada` (sigue 409
   para cualquier otro estado, p. ej. Reservada). Si estaba Disponible, pasa a
   Ocupada (igual que hoy); si ya estaba Ocupada, se queda así.
2. **`venta_service.cobrar`**: libera la mesa solo si **no queda otro pedido
   activo** en ella (consulta que excluye el pedido que se está cobrando —
   cuidado con el orden: la venta de este pedido aún no existía al entrar).
3. **`pedido_service.cancelar`**: misma condición al liberar.

Esto cierra de paso la deuda anotada en CONTEXTO §7: "`cobrar` y `cancelar`
ponen `mesa.estado = 'Disponible'` sin condición" — hoy inalcanzable, con esta
feature sería un bug real (cobrar la ronda 1 liberaría una mesa que aún debe la
ronda 2).

**Sin cambios de esquema ni de API pública:** mismos endpoints, mismos shapes;
solo cambia cuándo responde 409 y cuándo se libera la mesa.

### Guard de Ocupada (PR #24) — no cambia

Editar/gestionar el **estado** de la mesa a mano sigue igual de blindado: 409
con pedido activo, 422 al asignar "Ocupada" manualmente. Lo único nuevo es que
*crear pedidos* deja de estar limitado a mesas Disponibles.

### Móvil — pantalla de Mesas del mesero

- Las mesas **Ocupadas dejan de estar deshabilitadas**: al tocarlas se elige la
  mesa y se va al menú, igual que una Disponible (el carrito ya arranca limpio).
- La tarjeta Ocupada pierde la opacidad de "apagada" y muestra un hint —
  «Toca para agregar otro pedido» — para que el mesero sepa que es una acción
  válida y no un descuido.
- Estados no seleccionables (p. ej. Reservada u otros futuros) siguen
  deshabilitados. Helper puro `mesaSeleccionable(estado)` en
  `mobile/src/lib/mesero.ts` con test (allowlist: Disponible, Ocupada).
- "Mis pedidos" y Cocina no cambian: ya listan N pedidos y muestran la mesa de
  cada uno. Caja ya lista **cada pedido por cobrar por separado** — una mesa con
  dos rondas aparece dos veces, cada una con su total.

### Cobro por ronda (decisión de alcance)

Cada pedido conserva **su propia cuenta y su propio ticket** (venta 1:1 con
pedido, como hoy). Si la mesa tiene 3 rondas, caja cobra 3 veces (cada una puede
usar la división por artículos del PR #30). Una **cuenta consolidada por mesa**
(un solo cobro que junte todas las rondas) queda explícitamente fuera de este
slice — implicaría romper venta 1:1 con pedido, el mismo motivo por el que se
descartó la Opción B del split bill.

## Fuera de alcance

- Cuenta consolidada por mesa (ver arriba).
- Agregar artículos a un pedido **ya enviado** (editar la comanda en cocina).
  Cada ronda es un pedido nuevo.
- El pendiente de "cerrar sin cobro" para el Entregado que nadie paga — sigue
  siendo otra deuda; esta feature no lo toca (una ronda Entregada sin cobrar
  seguirá reteniendo la mesa, ahora junto con sus hermanas).

## Criterios de éxito

- Backend (tests nuevos): crear pedido sobre mesa Ocupada → 201 y la mesa sigue
  Ocupada; con dos rondas activas, cobrar una → mesa sigue Ocupada, cobrar la
  última → Disponible; lo mismo con cancelar; crear sobre Reservada → 409 (la
  regla vieja sobrevive para estados no operables).
- Móvil: `mesaSeleccionable` testeado; suite completa + `tsc` limpios.
- Smoke en dispositivo: dos rondas en la misma mesa (menú → confirmar dos
  veces), ambas visibles en Cocina y en Mis pedidos, cobrarlas por separado en
  Caja y verificar que la mesa se libera solo tras la segunda.
