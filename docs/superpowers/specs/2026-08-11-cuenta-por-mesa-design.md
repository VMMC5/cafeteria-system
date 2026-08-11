# Cuenta por mesa: venta multi-pedido — Diseño

**Fecha:** 2026-08-11 · **Rama:** `feature/cuenta-por-mesa` · **Estado:** aprobado por el usuario

## Problema

Con el PR #31 una mesa acepta varias rondas, pero cada ronda se cobra por separado
(venta 1:1 con pedido): el cliente que pidió tres veces recibe tres folios y Caja
hace tres cobros. La operación real es una **cuenta**: se acumulan rondas y, cuando
el cliente ya no quiere más, se cobra **todo junto** en un solo folio/ticket.

## Decisiones del usuario

1. **Modo de cobro — ambos:** el flujo principal es cobrar la cuenta completa de la
   mesa; Caja también puede cobrar una ronda suelta (p. ej. un comensal se va antes).
2. **División de cuenta (PR #30) sobre toda la cuenta:** al dividir entre personas se
   reparten los artículos de todas las rondas juntas.
3. **Bloqueo hasta entregar:** la cuenta completa solo se cobra cuando todas las
   rondas están Entregadas; si hay una en cocina, la app lo indica y no deja cobrar
   (siempre se puede cancelar esa ronda si el cliente se arrepintió).

## Enfoques evaluados

- **A. Venta multi-pedido (elegido):** invertir la FK — una venta cubre N pedidos de
  la misma mesa. Cambio de esquema mínimo con folio/ticket/pagos únicos reales.
- **B. Cobro por lote en el móvil (descartado):** N ventas creadas en secuencia desde
  Caja. Genera N folios para un solo pago real, reparto artificial de efectivo/cambio
  entre ventas, rompe el modelo de la calculadora del PR #30 y no es atómico.
- **C. Entidad `Cuenta` formal (descartado, YAGNI):** conceptualmente pura pero toca
  creación de pedidos, cocina, caja, web y reportes para el mismo resultado que A.
  Si algún día hay propinas/descuentos/reapertura de cuenta, se evoluciona desde A.

## Diseño (Opción A)

### Modelo y migración

- Nueva columna **`pedidos.id_venta`** (FK a `ventas.id_venta`, nullable). Pedido con
  `id_venta IS NULL` = ronda de cuenta abierta (o cancelada sin cobro).
- Se elimina **`ventas.id_pedido`**. Relaciones: `Venta.pedidos` (1:N), `Pedido.venta`.
- Migración Alembic con **backfill** (`pedidos.id_venta` se llena desde las ventas
  existentes 1:1) — sin pérdida hacia adelante. `downgrade` documentado como parcial:
  una venta multi-pedido no puede volver al modelo 1:1 (mismo criterio aceptado en la
  migración de inventario a 3 decimales).

### API y servicio

- `VentaCreate`: **`ids_pedidos: list[int]`** (mínimo 1, sin duplicados) reemplaza a
  `id_pedido`. El móvil es el único consumidor y se actualiza en el mismo PR — no hay
  endpoint nuevo ni retrocompatibilidad que mantener.
- Validaciones de `venta_service.cobrar` sobre la lista:
  - todos los pedidos existen (404), ninguno Cancelado (409), ninguno con venta previa
    (409) — reglas actuales aplicadas a N;
  - **todos de la misma mesa** (409) — una venta es la cuenta de una mesa;
  - con **más de un pedido, todos Entregados** (409 «la mesa tiene una ronda sin
    entregar»); la lista de uno conserva la regla actual (no romper el flujo existente).
- `total` = suma de `pedido.total`; pagos, regla de pago suficiente, excedente, folio
  único y ticket funcionan igual que hoy (un juego de pagos por cuenta).
- Liberación de mesa: `tiene_pedido_activo` generaliza `excepto_id_pedido` a una
  **lista** — la mesa se libera solo si no queda otro pedido activo fuera de los cobrados.
- `VentaOut`: `ids_pedidos` en lugar de `id_pedido`. Los `join` de `reporte_service`
  pasan de `Venta.id_pedido` a `Pedido.id_venta` (mismos números, cambia el camino).
- `GET /pedidos?por_cobrar=true` no cambia de forma; el móvil agrupa por mesa.

### Móvil (Caja)

- **`caja/index.tsx`:** la lista plana pasa a **tarjetas de cuenta por mesa**
  («Mesa 4 · 3 rondas · $540.00»). Si alguna ronda no está Entregada: badge «ronda en
  cocina» y cobro de cuenta deshabilitado. La tarjeta se expande para ver rondas y
  cobrar una suelta.
- **`caja/cobro.tsx`:** recibe uno o varios ids; muestra los artículos de todas las
  rondas con etiqueta discreta de ronda por sección; total = suma. Líneas de pago,
  regla de excedente solo-Efectivo y la **calculadora de división operan sobre la
  unión de líneas** — `lib/split.ts` es puro sobre líneas y no cambia.
- **`lib/ticket.ts`:** un folio; líneas de todas las rondas corridas, como cuenta de
  restaurante.
- Helpers puros nuevos en `lib/caja.ts`: agrupar pedidos por mesa y `cuentaCobrable`
  (todas las rondas Entregadas).

## Fuera de alcance

- Panel web: sin cambios (no consume `POST /ventas`).
- Propinas, descuentos, reapertura de cuentas, transferencia de rondas entre mesas.
- Cambios en mesero/cocina: las rondas se crean y avanzan igual que en el PR #31.

## Criterios de éxito

- Backend: cobrar 2 rondas → 201 con total sumado, folio único y mesa liberada;
  mesas distintas 409; ronda sin entregar en cuenta múltiple 409; ronda ya cobrada
  409; ronda suelta conserva el comportamiento actual (tests existentes verdes);
  reportes cuadran con una venta multi-pedido.
- Móvil: tests del agrupador y `cuentaCobrable`; flujo de cobro adaptado a
  `ids_pedidos`; división sobre unión de rondas; `tsc --noEmit` limpio.
- Smoke en dispositivo: dos rondas → cobrar la cuenta completa dividida entre dos
  personas → un folio, mesa liberada; ronda suelta cobrable por separado.

## Dependencias

Sale de `main` con los PRs #30 (división) y #31 (rondas) ya mergeados — ambos en main
desde el 2026-08-11.
