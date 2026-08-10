# Costo de insumo por promedio ponderado — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que cada compra actualice el costo del insumo con el promedio ponderado del inventario, en vez de pisarlo con el último costo pagado.

**Architecture:** Un helper puro `_costo_promedio` en `compra_service.py` (único archivo de producción tocado), aplicado en el bucle de `crear_compra` calculando con el stock previo antes de sumarlo. Tests unitarios del helper (patrón `test_venta_service.py`: importar y probar sin BD) + un test de integración por API + cierre de la deuda en los docs.

**Tech Stack:** FastAPI + SQLAlchemy + `decimal.Decimal` + pytest.

**Spec:** `docs/superpowers/specs/2026-08-09-costo-promedio-ponderado-design.md`

## Global Constraints

- Fórmula: `nuevo_costo = (stock_actual × costo_actual + cantidad × costo_compra) / (stock_actual + cantidad)`, cuantizado a `Decimal("0.01")` con `ROUND_HALF_UP`.
- Bordes: si `stock_actual <= 0` **o** `costo_actual == 0`, el costo nuevo es el de la compra tal cual (sin cuantizar de más: ya viene a 2 decimales del schema).
- **El promedio se calcula con el stock previo**: en el bucle, la asignación de costo va ANTES de sumar el stock.
- La columna `insumos.costo_unitario` sigue `Numeric(10,2)`: **sin migración**.
- No se tocan: `insumo_service` (el PATCH manual de costo se conserva), `receta_service`, `venta_service`, `seed_demo`, `MovimientoInventario`, schemas, ninguna pantalla ni template.
- `DetalleCompra.costo_unitario` conserva el costo pagado real (no se promedia).
- Los tests existentes de compras usan insumos con costo 0: deben seguir verdes **sin tocarlos**.
- Comentarios, docstrings y mensajes de commit en español; commits atómicos por tarea.

## Cómo correr los tests

Checkout principal: `docker compose exec api pytest -q`. En un **worktree**, `docker compose exec` corre `main` — usa el contenedor efímero (copia el `.env` del principal; no omitas `--user`, deja archivos root):

```bash
docker run --rm --network cafeteria-system_default --user 1000:1000 \
  --env-file <worktree>/.env -v <worktree>/backend:/code -w /code \
  cafeteria-system-api pytest -q
```

Baseline actual: backend **228** (web 126 y móvil 92 no se tocan en este slice).

---

## File Structure

- Modificar `backend/app/services/compra_service.py` — helper `_costo_promedio` + 2 líneas del bucle de `crear_compra` (orden invertido).
- Crear `backend/tests/test_compra_service.py` — tests unitarios del helper (sin BD).
- Modificar `backend/tests/test_compras_api.py` — 1 test de integración.
- Modificar `progress.md` y `CONTEXTO-PROYECTO.md` — cierre de la deuda.

---

## Task 1: Helper `_costo_promedio` con sus tests unitarios

**Files:**
- Modify: `backend/app/services/compra_service.py:1` (import) y nueva función a nivel de módulo
- Test: Create `backend/tests/test_compra_service.py`

**Interfaces:**
- Consumes: nada.
- Produces: `_costo_promedio(stock_actual: Decimal, costo_actual: Decimal, cantidad: Decimal, costo_compra: Decimal) -> Decimal` en `app.services.compra_service`. La Task 2 la llama desde el bucle de `crear_compra`.

- [ ] **Step 1: Escribir los tests que fallan**

Crea `backend/tests/test_compra_service.py` (mismo patrón que `test_venta_service.py`: importar la función y probarla sin BD):

```python
from decimal import Decimal

from app.services.compra_service import _costo_promedio


def test_promedio_ponderado_redondea_half_up():
    # 10 kg @ $95 + 8 kg @ $98.50 = $1738 / 18 = $96.5555… → $96.56
    r = _costo_promedio(
        Decimal("10"), Decimal("95.00"), Decimal("8"), Decimal("98.50")
    )
    assert r == Decimal("96.56")


def test_promedio_redondea_hacia_abajo_bajo_medio_centavo():
    # 10 @ $95 + 5 @ $95.10 = $1425.50 / 15 = $95.0333… → $95.03
    r = _costo_promedio(
        Decimal("10"), Decimal("95.00"), Decimal("5"), Decimal("95.10")
    )
    assert r == Decimal("95.03")


def test_stock_cero_toma_el_costo_de_la_compra():
    r = _costo_promedio(Decimal("0"), Decimal("95.00"), Decimal("8"), Decimal("98.50"))
    assert r == Decimal("98.50")


def test_costo_cero_toma_el_costo_de_la_compra():
    """Promediar contra stock valuado a $0 diluiría el costo con unidades que
    nadie pagó (10 pzas a $0 + 5 a $30 daría $10)."""
    r = _costo_promedio(Decimal("10"), Decimal("0"), Decimal("5"), Decimal("30.00"))
    assert r == Decimal("30.00")


def test_composicion_secuencial_dos_lineas():
    """Una compra con el mismo insumo en dos líneas promedia en cadena: la
    segunda línea parte del costo y stock resultantes de la primera."""
    paso1 = _costo_promedio(
        Decimal("10"), Decimal("95.00"), Decimal("8"), Decimal("98.50")
    )  # 96.56, stock queda en 18
    paso2 = _costo_promedio(Decimal("18"), paso1, Decimal("2"), Decimal("100.00"))
    # (18 × 96.56 + 2 × 100) / 20 = 1938.08 / 20 = 96.904 → 96.90
    assert paso2 == Decimal("96.90")


def test_stock_fraccionario_tres_decimales():
    """El stock es Numeric(10,3) desde el PR #26: el promedio opera con
    cantidades fraccionarias exactas."""
    # 0.500 kg @ $80 + 0.250 kg @ $92 = 40 + 23 = 63 / 0.75 = 84
    r = _costo_promedio(
        Decimal("0.500"), Decimal("80.00"), Decimal("0.250"), Decimal("92.00")
    )
    assert r == Decimal("84.00")
```

- [ ] **Step 2: Correr y verificar que fallan**

```bash
docker compose exec api pytest -q tests/test_compra_service.py
```

Esperado: FAIL — `ImportError: cannot import name '_costo_promedio'`.

- [ ] **Step 3: Implementar el helper**

En `backend/app/services/compra_service.py`, línea 1, amplía el import:

```python
from decimal import ROUND_HALF_UP, Decimal
```

Y añade la función a nivel de módulo, antes de `crear_compra`:

```python
def _costo_promedio(
    stock_actual: Decimal,
    costo_actual: Decimal,
    cantidad: Decimal,
    costo_compra: Decimal,
) -> Decimal:
    """Promedio ponderado del costo tras una compra, a 2 decimales.

    Si el inventario previo no tiene valor (stock <= 0 o costo 0), el costo
    nuevo es el de la compra: promediar contra valor cero diluiría el costo
    con unidades que nadie pagó.
    """
    if stock_actual <= 0 or costo_actual == 0:
        return costo_compra
    total_previo = stock_actual * costo_actual
    total_compra = cantidad * costo_compra
    return ((total_previo + total_compra) / (stock_actual + cantidad)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
```

- [ ] **Step 4: Correr y verificar que pasan**

```bash
docker compose exec api pytest -q tests/test_compra_service.py
```

Esperado: **6 passed.**

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/compra_service.py backend/tests/test_compra_service.py
git commit -m "feat(api): helper de costo promedio ponderado para compras

Fórmula clásica de promedio ponderado a 2 decimales (ROUND_HALF_UP), con el
borde de inventario sin valor (stock 0 o costo 0 → costo de la compra, para
no diluir con unidades que nadie pagó). Todavía sin cablear: la siguiente
tarea lo aplica en crear_compra."
```

---

## Task 2: Aplicar el promedio en `crear_compra` + test de integración

**Files:**
- Modify: `backend/app/services/compra_service.py:83-85` (el bucle de `crear_compra`)
- Test: `backend/tests/test_compras_api.py`

**Interfaces:**
- Consumes: `_costo_promedio(stock_actual, costo_actual, cantidad, costo_compra) -> Decimal` (Task 1, mismo módulo).
- Produces: nada (tarea terminal de código).

- [ ] **Step 1: Escribir el test de integración que falla**

Añade al final de `backend/tests/test_compras_api.py` (usa los helpers existentes `_proveedor_id`, `_stock_costo`; el insumo se crea con stock y costo iniciales reales vía API, no con el helper `_insumo` que fija costo 0):

```python
def test_compra_promedia_el_costo_del_insumo(client, db, cocinero_headers):
    """El costo del insumo es el promedio ponderado del inventario, no el
    último costo pagado: 10 kg @ $95 + 8 kg @ $98.50 → $96.56 (no $98.50).
    El detalle de la compra sí conserva el costo pagado real."""
    from app.models import UnidadMedida

    u = (
        db.query(UnidadMedida)
        .filter(UnidadMedida.nombre_unidad == "Kilogramo")
        .one()
        .id_unidad
    )
    ins = client.post(
        "/api/v1/insumos",
        headers=cocinero_headers,
        json={
            "nombre_insumo": "Café promedio",
            "id_unidad": u,
            "stock_actual": "10.000",
            "stock_minimo": 0,
            "costo_unitario": "95.00",
        },
    ).json()
    prov = _proveedor_id(client, cocinero_headers, "Tostadores Unidos")
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": prov,
            "items": [
                {
                    "id_insumo": ins["id_insumo"],
                    "cantidad": "8.000",
                    "costo_unitario": "98.50",
                }
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    # El detalle histórico conserva lo pagado, sin promediar.
    assert float(body["detalle"][0]["costo_unitario"]) == 98.50
    stock, costo = _stock_costo(client, cocinero_headers, ins["id_insumo"])
    assert stock == 18.0
    assert costo == 96.56
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
docker compose exec api pytest -q tests/test_compras_api.py::test_compra_promedia_el_costo_del_insumo
```

Esperado: FAIL — `costo == 98.5` (hoy el último costo pisa al anterior).

- [ ] **Step 3: Cablear el helper en el bucle**

En `crear_compra` (`backend/app/services/compra_service.py:83-85`), reemplaza:

```python
        insumo = insumos[item.id_insumo]
        insumo.stock_actual = insumo.stock_actual + item.cantidad
        insumo.costo_unitario = item.costo_unitario
```

por:

```python
        insumo = insumos[item.id_insumo]
        # El promedio usa el stock PREVIO: calcular el costo antes de sumar.
        # Si la compra repite un insumo en dos líneas, el dict comparte la
        # instancia y el promedio compone en cadena, línea a línea.
        insumo.costo_unitario = _costo_promedio(
            insumo.stock_actual,
            insumo.costo_unitario,
            item.cantidad,
            item.costo_unitario,
        )
        insumo.stock_actual = insumo.stock_actual + item.cantidad
```

- [ ] **Step 4: Correr el test y verificar que pasa**

```bash
docker compose exec api pytest -q tests/test_compras_api.py::test_compra_promedia_el_costo_del_insumo
```

Esperado: PASS.

- [ ] **Step 5: Correr la suite completa del backend**

```bash
docker compose exec api pytest -q
```

Esperado: **235 passed** (228 + 6 unitarios + 1 integración), 0 failed. En particular: `test_crear_compra_ok` (insumo con costo 0 espera 20.0 — el borde lo cubre) y `test_seed_demo.py` (compras al costo vigente: el promedio no las mueve) deben seguir verdes **sin tocarse**. Si alguno falla, es una regresión real del cableado — no ajustes el test.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/compra_service.py backend/tests/test_compras_api.py
git commit -m "feat(api): la compra promedia el costo del insumo en vez de pisarlo

crear_compra calcula el promedio ponderado con el stock previo (el orden de
las dos asignaciones se invierte a propósito) y el detalle de la compra
conserva el costo pagado real. Cierra la deuda de 'costo = último costo'."
```

---

## Task 3: Documentación

**Files:**
- Modify: `progress.md` — en "Deuda técnica", **eliminar** la línea «**Costo de insumo** por compra = último costo (no promedio ponderado).»; **añadir** las dos deudas nuevas de la spec: (a) el kárdex no registra costo por movimiento — sin histórico de valuación, el promedio solo vive en el estado actual del insumo; (b) la deriva de centavos por cuantizar a 2 decimales en cada compra es aceptada por diseño. En "Próximo": la entrada del slice como rama lista para PR (sin inventar número), con el conteo backend **235**.
- Modify: `CONTEXTO-PROYECTO.md` — §3 (flujo de negocio) dice «compra sube stock (kárdex Compra, costo = último costo)»: cambiar a promedio ponderado. Actualizar el conteo de backend a 235 con la nota de rama sin mergear.

**Interfaces:** ninguna.

- [ ] **Step 1: Aplicar los cambios descritos en Files**

- [ ] **Step 2: Verificar que no queda referencia a "último costo" como comportamiento vigente**

```bash
grep -rn "último costo" progress.md CONTEXTO-PROYECTO.md
```

Esperado: ninguna mención que lo describa como comportamiento actual (histórico/changelog está bien).

- [ ] **Step 3: Commit**

```bash
git add progress.md CONTEXTO-PROYECTO.md
git commit -m "docs: registra el promedio ponderado del costo de insumo y cierra la deuda"
```

---

## Verificación final antes del PR

- [ ] Suite backend completa: **235 passed**. (Web y móvil no se tocaron; no hace falta re-correrlas salvo que la revisión final lo pida.)
- [ ] Verificación manual del usuario (spec §Verificación):
  1. Insumo con 10 kg @ $95.00 (visible en Swagger, `GET /insumos/{id}`).
  2. Compra móvil de 8 kg @ $98.50 → el insumo queda en `96.56`, no en `98.50`.
  3. Segunda compra a precio distinto → el costo se mueve hacia el promedio.
  4. Compra sobre insumo recién creado (costo 0) → toma el costo de la compra.
