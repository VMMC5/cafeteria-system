# División de cuenta por artículos en Caja móvil — "calculadora de división" (Opción A)

**Fecha:** 2026-08-11 · **Decidido:** 2026-08-11 (Opción A elegida sobre la B de ventas/folios separados) · **Alcance:** solo móvil, sin cambios de backend ni web.

## Problema

"Cóbrame solo el capuchino y el pastel; mi amigo paga lo suyo." Hoy la pantalla de
cobro soporta pago dividido **por método** (N líneas de pago sobre el total), pero el
cajero tiene que calcular a mano cuánto le toca a cada persona. Dividir por artículos
es de lo más pedido en un POS y propenso a errores mentales con IVA de por medio.

## Fundamento que lo hace barato (verificado en el backend)

- `Pedido.total = Σ detalle.subtotal` y cada `subtotal = cantidad × precio_unitario`
  con el **precio final (IVA incluido)** congelado al crear el pedido
  (`backend/app/models/pedido.py:49`, `pedido_service.py:106`).
- La venta no suma IVA por encima: lo **desglosa** (`base = total/(1+tasa)`,
  `venta_service.desglose`).

Por lo tanto: lo que paga cada persona = **suma de los precios de sus unidades
asignadas**, exacto por construcción. No hay prorrateo de IVA, no hay residuos de
redondeo (precios a 2 decimales × unidades enteras), y la suma de personas siempre
cuadra con `pedido.total`.

- La API ya acepta N pagos por venta (`POST /ventas`, PR #22): cada persona se
  materializa como **una línea de pago** de la misma venta. Un solo folio/ticket.

## Diseño

### Lógica pura — `mobile/src/lib/split.ts` (TDD)

```ts
// Una "persona" es un índice 0..N-1. Una asignación reparte las unidades de una
// línea del pedido entre personas (los pedidos manejan cantidades enteras).
type Asignacion = number[][]; // asignacion[linea][persona] = unidades

crearAsignacion(numLineas, numPersonas): Asignacion  // todo en 0
asignar(a, linea, persona, delta): Asignacion         // +1/−1 con tope por unidades de la línea
unidadesAsignadas(a, linea): number
unidadesRestantes(a, linea, detalle): number
totalPersona(a, persona, detalle): number             // Σ unidades × precio_unitario
completa(a, detalle): boolean                         // todas las unidades asignadas
personasConConsumo(a): number[]                       // índices con total > 0
```

- Inmutable (devuelve copias), sin estado global; `detalle` es el `PedidoLinea[]`
  que ya trae la pantalla (con `precio_unitario` desde el PR #29).
- Agregar/quitar personas = redimensionar la matriz. **Al quitar una persona sus
  unidades regresan a "sin asignar"** (nunca se reasignan solas a otra persona).

### UI — sección "Dividir cuenta" en la pantalla de cobro (`caja/cobro.tsx`)

- Botón/toggle **"Dividir cuenta"** visible antes de cobrar, junto a "+ Agregar pago".
- Al activarlo se muestra el modo división:
  - Chips de personas (**Persona 1..N**, + para agregar, ✕ para quitar; mínimo 2).
    El chip seleccionado define la **persona activa**.
  - Por cada línea del pedido: nombre, precio unitario, cuántas unidades tiene la
    persona activa y un **stepper −/+** que le asigna/quita unidades a esa persona
    (tope: unidades de la línea); contador "quedan X por asignar" por línea.
  - Resumen en vivo: total por persona y "sin asignar: X unidades / $Y".
- Botón **"Aplicar división"** (habilitado solo con `completa()`): reemplaza las
  líneas de pago por una por persona con consumo, **monto prellenado** con
  `totalPersona` y método Efectivo por defecto — el cajero cambia método/referencia
  por línea con la UI existente. La etiqueta de la línea indica "Pago N · Persona M".
- Es una **calculadora**: tras aplicar, los montos siguen siendo editables y todas
  las reglas existentes se conservan (suma debe cubrir el total, excedente
  solo-Efectivo, referencia solo en no-Efectivo). Salir del modo división no borra
  las líneas aplicadas.
- El comprobante no cambia (un folio; los pagos ya se listan por método/referencia).

### Fuera de alcance

- Ventas/folios separados por comensal (Opción B) — requeriría romper venta 1:1
  con pedido (esquema, folios, reportes).
- Dividir una **unidad** entre varias personas ("a partes iguales el postre"):
  se pospone; el reparto es por unidades enteras. (La división en partes iguales
  del total ya se puede lograr hoy escribiendo montos a mano.)
- Persistir la división (quién comió qué) en la API: la venta guarda pagos, no
  personas.

## Criterios de éxito

- `lib/split.ts` con cobertura de: asignar/quitar unidades con topes, totales por
  persona exactos, `completa`, redimensionar personas, y la invariante
  `Σ totalPersona == pedido.total` cuando `completa()`.
- En la pantalla: aplicar una división de un pedido de ejemplo prellena N líneas
  de pago cuya suma es exactamente el total; el flujo de cobro existente (96 tests)
  sigue verde y `tsc` limpio.
- Smoke en dispositivo: pedido con 2+ productos y cantidades > 1, dividido entre
  2–3 personas con métodos mixtos, cobra 201 y el ticket lista los pagos.
