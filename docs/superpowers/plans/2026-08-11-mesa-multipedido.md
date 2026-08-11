# Varios pedidos por mesa — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que una mesa Ocupada acepte pedidos adicionales ("rondas") y que la mesa se libere solo al cerrar (cobrar o cancelar) el último pedido activo; en el móvil, que el mesero pueda tocar una mesa Ocupada para ordenar de nuevo.

**Architecture:** Tres cambios puntuales de reglas en los services del backend (sin esquema ni API pública nuevos): `crear` acepta `{Disponible, Ocupada}`, y la liberación de mesa en `cobrar`/`cancelar` pasa de incondicional a consultar si quedan otros pedidos activos — reutilizando `tiene_pedido_activo` (PR #24) con exclusión del pedido que se está cerrando. En el móvil solo cambia la pantalla de Mesas (tarjetas Ocupadas tocables con hint) sobre un helper puro `mesaSeleccionable`.

**Tech Stack:** FastAPI + SQLAlchemy (backend), Expo/React Native + Jest (móvil). Web sin cambios.

**Spec:** `docs/superpowers/specs/2026-08-11-mesa-multipedido-design.md`

## Global Constraints

- **Sin cambios de esquema, migraciones ni shapes de API** — solo cuándo responde 409 y cuándo se libera la mesa.
- **El guard del PR #24 no se relaja:** editar el *estado* de la mesa a mano sigue rechazando 409/422 igual que hoy (`test_mesas_api.py` debe quedar intacto y verde).
- La exclusión del pedido en cierre se hace **por parámetro** (`excepto_id_pedido`) en `tiene_pedido_activo`, no leyendo estado a medio commit — el orden venta/consulta dentro de `cobrar` no debe depender del flush.
- **Idioma:** comentarios, mensajes y commits en español. **Commits atómicos** por tarea con su test.

## Cómo correr los tests

Desde el **worktree**, `docker compose exec` corre el código de `main`. Usa contenedor efímero montando el worktree (el `.env` ya está copiado). **No omitas `--user`**: sin él pytest deja `__pycache__` de root y luego el worktree no se puede borrar.

```bash
# Backend (requiere el stack del worktree o al menos su db arriba)
docker run --rm --network <proyecto>_default \
  --user $(id -u):$(id -g) \
  --env-file /home/vikca/cafeteria-system/.claude/worktrees/mesa-multipedido/.env \
  -v /home/vikca/cafeteria-system/.claude/worktrees/mesa-multipedido/backend:/code -w /code \
  cafeteria-system-api pytest -q

# Móvil
cd mobile && npm install   # primera vez
npm test && npx tsc --noEmit
```

> El stack del worktree crea proyecto Compose propio con BD vacía (memoria
> `worktree-compose-proyecto-aislado`): `up -d` + `alembic upgrade head` + seeds
> antes de correr nada; los tests de backend autoprovisionan su BD `_test`.

## File Structure

```
backend/app/services/pedido_service.py   (edit)  crear acepta Ocupada; cancelar condicional; tiene_pedido_activo(excepto)
backend/app/services/venta_service.py    (edit)  cobrar libera condicional
backend/tests/test_pedidos_api.py        (edit)  mesa Ocupada ahora 201; Reservada sigue 409
backend/tests/test_ventas_api.py         (edit)  +tests de liberación con dos rondas
mobile/src/lib/mesero.ts                 (edit)  mesaSeleccionable(estado)
mobile/src/lib/mesero.test.ts            (edit)  su test
mobile/src/app/mesero/mesas.tsx          (edit)  Ocupada tocable + hint
```

---

## Tarea 1 — Backend: crear pedido sobre mesa Ocupada

- [ ] **RED** — en `backend/tests/test_pedidos_api.py`:
  - Reescribir `test_mesa_ocupada_409` como `test_segundo_pedido_sobre_mesa_ocupada_201`:
    crear un pedido (mesa pasa a Ocupada) y crear un **segundo** sobre la misma
    mesa → 201, la mesa sigue `"Ocupada"`, y ambos pedidos existen con detalle
    propio.
  - Nuevo `test_pedido_sobre_mesa_reservada_409`: mesa en `"Reservada"`
    (transición válida desde Disponible, ver `test_disponible_a_reservada_ok`)
    → `POST /pedidos` responde 409.
- [ ] Correr solo ese archivo → los dos tests nuevos fallan.
- [ ] **GREEN** — `pedido_service.crear`: el guard pasa de
      `mesa.estado != "Disponible"` a `mesa.estado not in ("Disponible", "Ocupada")`
      (mensaje 409 sin cambios); `mesa.estado = "Ocupada"` se queda como está
      (idempotente si ya estaba).
- [ ] Archivo de tests en verde.
- [ ] Commit: `feat(api): una mesa Ocupada acepta pedidos adicionales (rondas)`

## Tarea 2 — Backend: liberar la mesa solo al cerrar la última ronda

- [ ] **RED** — tests nuevos:
  - En `test_ventas_api.py`: dos rondas activas en la misma mesa → cobrar la
    primera → la mesa sigue `"Ocupada"`; cobrar la segunda → `"Disponible"`.
  - En `test_pedidos_api.py` (o donde viven los de cancelación): dos rondas →
    cancelar una → mesa `"Ocupada"`; cancelar la otra → `"Disponible"`.
  - Mixto: una ronda cobrada y la otra cancelada → `"Disponible"` al final.
- [ ] **GREEN**:
  - `tiene_pedido_activo(db, id_mesa, excepto_id_pedido: int | None = None)` —
    añade `Pedido.id_pedido != excepto_id_pedido` cuando se pasa.
  - `venta_service.cobrar`: `pedido.mesa.estado = "Disponible"` → solo si
    `not tiene_pedido_activo(db, pedido.id_mesa, excepto_id_pedido=pedido.id_pedido)`.
  - `pedido_service.cancelar`: misma condición (nota: al consultar, el pedido
    ya tiene `id_estado = Cancelado` en la sesión, pero la exclusión explícita
    lo hace robusto al orden de flush).
- [ ] **Suite backend completa** (los tests viejos de "mesa Disponible tras
      cobrar/cancelar" con una sola ronda deben seguir verdes sin editarlos).
- [ ] Commit: `feat(api): la mesa se libera solo al cerrar el último pedido activo`

## Tarea 3 — Móvil: mesas Ocupadas tocables

- [ ] **RED** — `mobile/src/lib/mesero.test.ts`: `mesaSeleccionable("Disponible")`
      y `("Ocupada")` → true; `("Reservada")` y cualquier otro → false.
- [ ] **GREEN** — helper en `mobile/src/lib/mesero.ts` (allowlist explícita).
- [ ] `mesas.tsx`:
  - `disabled={!mesaSeleccionable(item.estado)}` y la opacidad "apagada" solo
    para no-seleccionables; el badge conserva su variante actual
    (Disponible ok / Ocupada busy / resto warn).
  - En tarjetas Ocupadas, hint bajo el badge: «Toca para agregar otro pedido»
    (fuente `body` 12, color muted).
  - Subtítulo de la pantalla: «Elige una mesa disponible» → «Elige una mesa;
    las ocupadas aceptan otra ronda» (o similar corto).
- [ ] `npm test` completo + `tsc --noEmit` limpios.
- [ ] Commit: `feat(mobile): tocar una mesa Ocupada abre el menú para otra ronda`

## Tarea 4 — Verificación final y PR

- [ ] Suite backend completa en contenedor efímero (esperado: 235 + ~6 nuevos).
- [ ] Suite móvil completa + `tsc` (esperado: 108 + ~1-2 nuevos sobre la rama
      de split-bill… **ojo:** esta rama sale de `main` sin el PR #30; el
      conteo base local es 96 + nuevos. Sin conflicto de archivos entre ambas).
- [ ] **Smoke en dispositivo (manual, con el usuario):** dos rondas en la misma
      mesa desde el móvil → ambas en Cocina y Mis pedidos → cobrarlas por
      separado en Caja → la mesa se libera solo tras la segunda. Verificar
      también que Reservada (desde el panel web) sigue sin ser tocable.
- [ ] Actualizar `progress.md` en la rama (sección + deuda de liberación
      incondicional cerrada).
- [ ] Push + PR hacia `main`.
