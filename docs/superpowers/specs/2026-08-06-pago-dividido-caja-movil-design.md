# Spec — Pago dividido en la Caja móvil

**Fecha:** 2026-08-06 · **Alcance:** solo `mobile/` (React Native + Expo). Sin cambios en la API.

## Objetivo

Cerrar el pendiente "Pago dividido en la Caja móvil": la API acepta N pagos por venta (`VentaCreate.pagos`, mín. 1, con `referencia` opcional y validación `suma ≥ total`), pero la pantalla de cobro solo permite un método. La Caja debe poder cobrar con varios métodos en un mismo cobro.

## Decisiones tomadas (brainstorming)

1. **UX — lista dinámica de pagos**: el cobro arranca con una línea (método + monto) y "+ Agregar pago" añade líneas (✕ para quitar con 2+). Resumen vivo Total / Pagado / Falta / Cambio. El flujo de un solo pago queda idéntico en pasos.
2. **Regla de excedente — solo Efectivo**: la suma puede exceder el total únicamente si hay una línea de Efectivo (el cambio sale de ahí); las líneas no-Efectivo deben sumar ≤ total. Regla solo en cliente; la API queda como está (`cambio = suma − total`).
3. **Referencia por pago**: campo opcional "Referencia" visible solo en líneas no-Efectivo (folio de voucher/transferencia). Se manda a la API con trim; si queda vacía se omite (null).
4. **Estructura**: lógica pura en `src/lib/caja.ts` con tests jest (convención del proyecto: lógica testeable en `lib/`, pantallas delgadas); nada de hooks custom ni componentes nuevos.

## Lógica (`src/lib/caja.ts`)

Se **sustituyen** `cambio(recibido, total)` y `puedeCobrar(recibido, total)` (la pantalla de cobro era su único consumidor) por funciones sobre la lista:

```ts
type PagoLinea = { id_metodo_pago: number; monto: number; referencia?: string };

sumaPagos(pagos: PagoLinea[]): number
faltante(pagos: PagoLinea[], total: number): number        // max(0, total − suma)
cambioPagos(pagos: PagoLinea[], total: number): number     // max(0, suma − total)
puedeCobrarPagos(pagos: PagoLinea[], total: number, idEfectivo: number | null): boolean
aPayload(pagos: PagoLinea[]): PagoIn[]
```

`puedeCobrarPagos` exige: `total > 0`; ≥1 línea; toda línea con `monto > 0`; `suma ≥ total`; y **suma de líneas con `id_metodo_pago !== idEfectivo` ≤ total** (el excedente solo puede venir de Efectivo). Con `idEfectivo === null` (catálogo sin método "Efectivo"), esa condición degrada a exigir suma exacta — seguro, no roto.

`idEfectivo` lo resuelve la pantalla: `metodos.find(m => m.nombre_metodo === "Efectivo")?.id_metodo_pago ?? null`.

En `src/api/client.ts` solo se amplía el tipo del elemento de `pagos` con `referencia?: string`.

## UI (`src/app/caja/cobro.tsx`)

- Estado: `lineas: { id_metodo_pago: number | null; montoTxt: string; referencia: string }[]`; inicial una línea con el primer método del catálogo preseleccionado (como hoy).
- Por línea: chips de método (mismo estilo actual), input de monto (`keyboardType="numeric"`), input "Referencia (opcional)" solo si el método elegido no es Efectivo, botón ✕ visible con 2+ líneas.
- "+ Agregar pago" añade línea (método: el primero del catálogo). Resumen vivo con `money()`: Total, Pagado, Falta, Cambio.
- Texto de ayuda cuando la suma excede el total sin línea de Efectivo: "El excedente solo se permite en Efectivo".
- Botón "Confirmar cobro" habilitado por `puedeCobrarPagos` (líneas parseadas con `Number(montoTxt) || 0`, filtrando `id_metodo_pago null` como inválidas).
- Confirmar: `cobrarVenta(access, pid, aPayload(lineasParseadas))`.
- Comprobante: ya pinta N pagos; único ajuste, mostrar `(referencia)` junto al método cuando exista.

## Errores y edge cases

- 409 (pedido cancelado / ya cobrado): manejo actual intacto (Alert + volver a `/caja`).
- 422 "Pago insuficiente": inalcanzable con la validación local; cubierto por el catch genérico existente.
- Montos no numéricos → `Number() || 0` → línea inválida → botón deshabilitado (sin crash).
- Importes de la API: siguen llegando por `coerceDecimals` y se muestran con `money()`; prohibido `.toFixed` directo sobre valores de la API (regla del proyecto).

## Tests (`src/lib/caja.test.ts`, TDD)

Se reescriben los 2 tests actuales hacia la nueva API. Cobertura mínima (~10 casos):

- `sumaPagos` / `faltante` / `cambioPagos` con 0, 1 y N líneas.
- Regla de Efectivo: excedente con línea de Efectivo ✓; excedente solo con tarjeta ✗; líneas no-Efectivo sumando > total ✗; suma exacta sin Efectivo ✓; `idEfectivo null` exige suma exacta.
- Inválidos: línea con `monto 0`, lista vacía, `total 0`.
- `aPayload`: referencia con trim; omitida si queda vacía; montos numéricos.

Cierre: `cd mobile && npm test` (58 → ~66) y `npx tsc --noEmit` limpio.

## Fuera de alcance

- Cambios en la API (reglas de cambio por método, validaciones nuevas).
- Reglas de negocio de propinas o descuentos (no existen en el sistema).
- Persistir borradores de cobro (la pantalla es efímera como hoy).
- Web admin (no cobra).
