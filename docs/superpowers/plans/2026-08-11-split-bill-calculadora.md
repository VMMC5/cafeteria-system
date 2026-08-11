# División de cuenta por artículos (calculadora) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** En la pantalla de cobro de Caja, permitir asignar los artículos del pedido a "personas" y prellenar una línea de pago por persona con su monto exacto, reutilizando íntegro el flujo de pago dividido existente (un solo folio/ticket, sin cambios de backend).

**Architecture:** Toda la aritmética vive en un módulo puro nuevo (`mobile/src/lib/split.ts`) que opera sobre una matriz inmutable `asignacion[línea][persona] = unidades`; la pantalla de cobro solo pinta esa matriz y, al aplicar, la traduce a las `LineaUI` de pago que ya existen. Los montos son exactos por construcción: los precios del detalle ya incluyen IVA (`Pedido.total = Σ cantidad × precio_unitario`; la venta solo desglosa), así que no hay prorrateo ni redondeo.

**Tech Stack:** Expo/React Native + TypeScript + Jest (solo móvil).

**Spec:** `docs/superpowers/specs/2026-08-11-split-bill-calculadora-design.md`

## Global Constraints

- **Backend y web no se tocan.** Ningún archivo fuera de `mobile/`.
- **`lib/caja.ts` no se modifica**: las reglas de pago (suma cubre total, excedente solo-Efectivo, referencia en no-Efectivo) ya están testeadas y la división solo *prellena* montos.
- **Inmutabilidad:** cada operación de `split.ts` devuelve una matriz nueva; nada muta argumentos.
- **Unidades enteras:** los pedidos manejan `cantidad: int`; no existe dividir media unidad.
- **Idioma:** comentarios, textos de UI y commits en español, como el resto del repo.
- **Commits atómicos** por tarea, con el test que la respalda.

## Cómo correr los tests

El móvil corre fuera de Docker; desde el worktree basta:

```bash
cd <worktree>/mobile && npm install   # solo la primera vez (node_modules no viaja)
npm test                              # suite jest (96 en main)
npx tsc --noEmit                      # tipos
```

## File Structure

```
mobile/src/lib/split.ts            (nuevo)  aritmética pura de la división
mobile/src/lib/split.test.ts       (nuevo)  su suite
mobile/src/app/caja/cobro.tsx      (edit)   sección "Dividir cuenta" + aplicar
```

---

## Tarea 1 — Núcleo de `split.ts`: crear y asignar unidades

`Asignacion = number[][]` (`asignacion[linea][persona] = unidades`). El tope por
línea llega como argumento (`unidadesLinea`), no se lee de estado global.

- [ ] **RED** — `mobile/src/lib/split.test.ts`:
  - `crearAsignacion(3, 2)` → matriz 3×2 llena de ceros.
  - `asignar(a, 0, 1, +1, 2)` asigna una unidad a la persona 1 y **no muta** `a`.
  - `asignar` con `delta` que rebasa el tope de la línea (suma de todas las
    personas > `unidadesLinea`) devuelve la matriz sin cambios.
  - `asignar` con `delta` negativo no baja de 0.
  - `unidadesAsignadas(a, linea)` y `unidadesRestantes(a, linea, unidadesLinea)`.
- [ ] Correr `npx jest src/lib/split.test.ts` → falla (módulo no existe).
- [ ] **GREEN** — implementar `crearAsignacion`, `asignar`, `unidadesAsignadas`,
      `unidadesRestantes` en `mobile/src/lib/split.ts`.
- [ ] `npx jest src/lib/split.test.ts` en verde; `npx tsc --noEmit` limpio.
- [ ] Commit: `feat(mobile): núcleo de la división de cuenta — matriz de asignación con topes (lib/split.ts)`

## Tarea 2 — Totales por persona e invariante de completitud

Usa `PedidoLinea[]` real (con `precio_unitario` y `cantidad`) como referencia.

- [ ] **RED** — agregar a `split.test.ts` con un detalle de ejemplo
      (2 × Café $44.40, 1 × Pastel $55.00, 3 × Galleta $12.00):
  - `totalPersona(a, persona, detalle)` suma `unidades × precio_unitario`.
  - `completa(a, detalle)` solo cuando **todas** las unidades están asignadas.
  - `personasConConsumo(a)` devuelve los índices con total > 0, en orden.
  - **Invariante:** con la asignación completa (repartida entre 3 personas de
    forma irregular), `Σ totalPersona == Σ cantidad × precio_unitario` exacto.
- [ ] **GREEN** — implementar `totalPersona`, `completa`, `personasConConsumo`.
- [ ] Suite del archivo en verde; `tsc` limpio.
- [ ] Commit: `feat(mobile): totales por persona y completitud de la división (lib/split.ts)`

## Tarea 3 — Alta y baja de personas

- [ ] **RED**:
  - `agregarPersona(a)` añade una columna en 0 a cada línea.
  - `quitarPersona(a, persona)` elimina la columna y **sus unidades regresan a
    "sin asignar"** (la suma asignada de cada línea baja; nadie hereda).
  - `quitarPersona` con 2 personas devuelve la matriz sin cambios (mínimo 2).
- [ ] **GREEN** — implementar ambas.
- [ ] Suite en verde; `tsc` limpio.
- [ ] Commit: `feat(mobile): alta y baja de personas en la división (lib/split.ts)`

## Tarea 4 — UI del modo división en `caja/cobro.tsx`

Estado nuevo en la pantalla: `dividiendo: boolean`, `asignacion: Asignacion | null`,
`personaActiva: number`. Sin tocar la lógica de pago existente.

- [ ] Botón **"Dividir cuenta"** (estilo outline, junto a "+ Agregar pago"); al
      activarlo crea `crearAsignacion(detalle.length, 2)` y muestra la sección:
  - Chips **Persona 1..N** (el seleccionado = persona activa) + chip "+" para
    `agregarPersona` y "✕" en el chip activo para `quitarPersona` (mín. 2).
  - Por línea del pedido: nombre, `precio_unitario`, unidades de la persona
    activa con `Stepper` −/+ (de `@/ui`, tope = `unidadesRestantes` + las suyas)
    y contador "quedan X por asignar" cuando `unidadesRestantes > 0`.
  - Resumen en vivo: `Persona N — $total` por cada persona, y "Sin asignar:
    X unidades · $Y" mientras no esté completa.
- [ ] Botón **"Aplicar división"** habilitado solo con `completa()`: reemplaza
      `lineas` por una `LineaUI` por elemento de `personasConConsumo`, con
      `montoTxt = totalPersona(...).toFixed(2)`, método por defecto
      `metodos[0]` y `etiqueta: "Persona N"` (campo opcional nuevo en `LineaUI`,
      mostrado en el encabezado de la línea como "Pago i · Persona N"). Cierra el
      modo división (`dividiendo = false`) sin borrar la asignación (reabrir la
      conserva para retocar).
- [ ] Verificación estática: `npx tsc --noEmit` limpio y `npm test` completo en
      verde (nada de lo existente se rompe).
- [ ] Commit: `feat(mobile): sección Dividir cuenta en el cobro — asignación por persona y prellenado de pagos`

## Tarea 5 — Verificación final y PR

- [ ] Suite móvil completa + `tsc` (esperado: 96 + ~12-15 nuevos, todos verdes).
- [ ] Levantar stack del worktree si hace falta smoke (`docker compose up -d` en
      el worktree crea proyecto propio con BD vacía: `alembic upgrade head` +
      `seed` + `seed_demo`; ver memoria `worktree-compose-proyecto-aislado`) o
      usar el stack principal con la app apuntada a él.
- [ ] **Smoke en dispositivo (manual, con el usuario):** pedido con 2+ productos
      y una cantidad > 1 → Dividir cuenta entre 3 personas (una sin consumo) →
      Aplicar → cambiar el método de una línea a Tarjeta con referencia →
      cobrar → 201, ticket con los pagos correctos y suma exacta.
- [ ] Actualizar `progress.md` (sección del slice + conteo de tests) dentro de la rama.
- [ ] Push + PR hacia `main` con el resumen del spec.
