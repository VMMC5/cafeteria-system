# Inventario a 3 decimales — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ampliar las cuatro columnas de cantidad del inventario de `Numeric(10,2)` a `Numeric(10,3)` para que el stock y el kárdex representen exactamente lo que consume una receta, rechazando con 422 las cantidades con más de 3 decimales.

**Architecture:** Migración Alembic sobre cuatro columnas (una de ellas requiere recrear una columna generada), validación `decimal_places=3` en el borde Pydantic, y una regla de presentación compartida —cantidades sin ceros de relleno— implementada en el móvil con un helper `cantidad()` y en el panel con un tipo marcador `Cantidad(float)` que sobrevive al tipado numérico del XLSX. Ningún servicio cambia: sus operaciones ya son `Decimal` y pasan a ser exactas.

**Tech Stack:** FastAPI + SQLAlchemy 2 + Alembic + Postgres (backend), Flask + Jinja + openpyxl/WeasyPrint (panel web), Expo/React Native + Jest (móvil).

**Spec:** `docs/superpowers/specs/2026-08-09-inventario-3-decimales-design.md`

## Global Constraints

- **Cantidades de inventario:** `Numeric(10, 3)` en el modelo, `Field(max_digits=10, decimal_places=3)` en Pydantic. Tope real: `9 999 999.999`.
- **El dinero NO se toca.** `costo_unitario`, `precio_venta`, `precio_unitario`, `monto`, `total`, `subtotal` siguen en 2 decimales y sin `decimal_places` en Pydantic. Ninguna tarea de este plan modifica un campo monetario.
- **Ningún servicio cuantiza.** La validación vive en Pydantic; la columna es la red de seguridad. `insumo_service`, `compra_service` y `receta_service` no se modifican en todo el plan.
- **Presentación de cantidades:** hasta 3 decimales, sin ceros de relleno. `500`, `12.5`, `0.125` — nunca `500.000` ni `0.13`.
- **Idioma:** comentarios, docstrings y mensajes de commit en español, como el resto del repo.
- **Commits atómicos** por tarea, con el test que la respalda.

## Cómo correr los tests

Si trabajas en el **checkout principal**:

```bash
docker compose exec api pytest -q          # backend
docker compose exec web pytest -q          # panel web
cd mobile && npm test                      # móvil
cd mobile && npx tsc --noEmit              # tipos del móvil
```

Si trabajas en un **worktree**, `docker compose exec` corre el código de `main`, no el tuyo. Usa un contenedor efímero que monte el worktree (copia antes el `.env` del checkout principal, está gitignorado). **No omitas `--user`**: sin él pytest deja `__pycache__` como root y `git worktree remove` falla después.

```bash
docker run --rm --network cafeteria-system_default \
  --user $(id -u):$(id -g) \
  --env-file <worktree>/.env \
  -v <worktree>/backend:/code -w /code \
  cafeteria-system-api pytest -q
```

## La trampa de la BD de test (léelo antes de la Tarea 1)

`backend/tests/conftest.py:72-83` crea la BD `cafeteria_db_test` solo si no existe y aplica el esquema con `Base.metadata.create_all`. **Ninguna de las dos cosas altera tablas existentes.** Si la BD de test ya está creada con `numeric(10,2)`, los tests de 3 decimales fallan aunque el modelo esté correcto, y el fallo parece un bug del código.

Por eso la Tarea 1 tira la BD de test **dos veces**: una antes de la corrida RED (para que el fallo sea el real, no un residuo) y otra antes de la GREEN (porque la corrida RED la volvió a crear con la escala vieja).

```bash
docker compose exec -T db psql -U cafeteria -d cafeteria_db \
  -c 'DROP DATABASE IF EXISTS cafeteria_db_test'
```

Este comando toca **solo** la base `_test`; la BD de desarrollo con los datos demo no se ve afectada.

---

## File Structure

**Backend**
- Modificar `backend/app/models/inventario.py:33-34,59` — `stock_actual`, `stock_minimo`, `MovimientoInventario.cantidad` a `Numeric(10,3)`.
- Modificar `backend/app/models/compra.py:56` — `DetalleCompra.cantidad` a `Numeric(10,3)`.
- Crear `backend/alembic/versions/7f3a9c2b1d84_inventario_3_decimales.py` — la migración.
- Modificar `backend/app/schemas/insumo.py:18-19,26,33` — validación de 3 decimales.
- Modificar `backend/app/schemas/compra.py:26` — íd.
- Modificar `backend/app/schemas/receta.py:8,12` — íd.
- Modificar `backend/tests/test_insumos_api.py`, `test_compras_api.py`, `test_recetas_api.py`, `test_schemas.py`.

**Móvil**
- Crear `mobile/src/lib/decimales.ts` — `normalizar`, `decimalesValidos`, `aCantidad`. Único lugar donde vive el regex.
- Crear `mobile/src/lib/decimales.test.ts`.
- Modificar `mobile/src/lib/recetas.ts` — `cantidadValida` a 3 decimales; `normalizar`/`aCantidad` se mudan a `decimales.ts` y se re-exportan.
- Modificar `mobile/src/lib/inventario.ts` — `movimientoValido` valida decimales.
- Modificar `mobile/src/lib/compras.ts` — `lineaCompraValida` valida decimales.
- Modificar `mobile/src/lib/format.ts` — helper `cantidad()`.
- Modificar las 4 pantallas de despliegue: `cocina/inventario.tsx`, `cocina/ajuste.tsx`, `cocina/receta-detalle.tsx`, `cocina/compra-nueva.tsx`.
- Modificar los tests: `recetas.test.ts`, `inventario.test.ts`, `compras.test.ts`, `format.test.ts`.

**Web**
- Modificar `web/app/reportes/routes.py` — `Cantidad`, `_cantidad`, rama en `_fmt_cell`, uso en la fila de inventario.
- Modificar `web/tests/test_reportes.py`.

**Docs**
- Modificar `README.md`, `progress.md`, `CONTEXTO-PROYECTO.md`.

---

## Task 1: Esquema a 3 decimales + migración Alembic

Amplía las cuatro columnas y escribe la migración. El caso de `detalle_compra` es especial: su columna `subtotal` es generada y depende de `cantidad`, y Postgres rechaza el `ALTER` mientras exista.

**Files:**
- Modify: `backend/app/models/inventario.py:33-34,59`
- Modify: `backend/app/models/compra.py:56`
- Create: `backend/alembic/versions/7f3a9c2b1d84_inventario_3_decimales.py`
- Test: `backend/tests/test_insumos_api.py`, `backend/tests/test_compras_api.py`, `backend/tests/test_recetas_api.py`

**Interfaces:**
- Consumes: nada (primera tarea).
- Produces: columnas `insumos.stock_actual`, `insumos.stock_minimo`, `movimientos_inventario.cantidad`, `detalle_compra.cantidad` con escala 3. La Tarea 2 asume que ya guardan milésimas sin redondear.

- [ ] **Step 1: Tirar la BD de test para que la corrida RED sea honesta**

```bash
docker compose exec -T db psql -U cafeteria -d cafeteria_db \
  -c 'DROP DATABASE IF EXISTS cafeteria_db_test'
```

- [ ] **Step 2: Escribir los tests que fallan — inventario y kárdex**

Añade al final de `backend/tests/test_insumos_api.py`, y `from decimal import Decimal` al principio del archivo:

```python
def test_stock_admite_3_decimales(client, db, cocinero_headers):
    """El inventario debe representar milésimas: con Numeric(10,2) un stock de
    0.125 kg se guardaba como 0.13 y el kárdex dejaba de cuadrar con la receta
    que lo consumió (cantidad_requerida siempre fue Numeric(10,3))."""
    r = _crear_insumo(
        client, db, cocinero_headers, nombre="Canela molida",
        stock="0.125", minimo="0.005",
    )
    assert r.status_code == 201
    body = r.json()
    assert Decimal(body["stock_actual"]) == Decimal("0.125")
    assert Decimal(body["stock_minimo"]) == Decimal("0.005")


def test_movimiento_admite_3_decimales(client, db, cocinero_headers):
    insumo = _crear_insumo(
        client, db, cocinero_headers, nombre="Clavo de olor", stock="1.000"
    ).json()
    r = _movimiento(
        client, cocinero_headers, insumo["id_insumo"], "Salida", "Merma", "0.125"
    )
    assert r.status_code == 200
    assert Decimal(r.json()["stock_actual"]) == Decimal("0.875")
```

Las cantidades van como **string** en el JSON, no como float: Pydantic las convierte a `Decimal` sin pasar por la representación binaria de un float, que es justo lo que este test mide.

- [ ] **Step 3: Escribir el test que falla — compra fraccionaria**

Añade al final de `backend/tests/test_compras_api.py`, y `from decimal import Decimal` al principio:

```python
def test_compra_admite_3_decimales_y_subtotal_cuadra(client, db, cocinero_headers):
    """La cantidad comprada llega al kárdex sin redondear, y el subtotal —columna
    generada en la BD— sigue calculándose sobre la cantidad exacta."""
    prov = _proveedor_id(client, cocinero_headers, "Especias del Sur")
    ins = _insumo(client, db, cocinero_headers, nombre="Nuez moscada", stock=0)
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": prov,
            "items": [
                {
                    "id_insumo": ins["id_insumo"],
                    "cantidad": "0.125",
                    "costo_unitario": "100.00",
                }
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert Decimal(body["detalle"][0]["cantidad"]) == Decimal("0.125")
    assert Decimal(body["detalle"][0]["subtotal"]) == Decimal("12.50")
    stock, _ = _stock_costo(client, cocinero_headers, ins["id_insumo"])
    assert stock == 0.125
```

- [ ] **Step 4: Escribir el test que falla — consumo exacto por receta**

Este es el caso que motiva todo el slice. Añade al final de `backend/tests/test_recetas_api.py`:

```python
def test_consumo_receta_3_decimales_exacto(client, db, admin_headers, cocinero_headers):
    """0.125 × 3 = 0.375 exacto. Con el inventario en 2 decimales cada línea de
    receta se redondeaba a 0.13 al descontar y el stock derivaba del kárdex."""
    pid = _producto_id(client, db, admin_headers, nombre="Chai especiado")
    iid = _insumo_id(client, db, cocinero_headers, nombre="Cardamomo", stock=1.0)
    client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=cocinero_headers,
        json={"id_insumo": iid, "cantidad_requerida": "0.125"},
    )
    mesa = _mesa_id(client, admin_headers, 731)
    r = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={"id_mesa": mesa, "items": [{"id_producto": pid, "cantidad": 3}]},
    )
    assert r.status_code == 201
    assert _stock(client, cocinero_headers, iid) == 0.625
```

El descuento ocurre **al crear el pedido** (`receta_service.consumir`), no al entregarlo. `1.0 − 0.375 = 0.625`.

- [ ] **Step 5: Correr los tests y verificar que fallan**

```bash
docker compose exec api pytest -q \
  tests/test_insumos_api.py::test_stock_admite_3_decimales \
  tests/test_insumos_api.py::test_movimiento_admite_3_decimales \
  tests/test_compras_api.py::test_compra_admite_3_decimales_y_subtotal_cuadra \
  tests/test_recetas_api.py::test_consumo_receta_3_decimales_exacto
```

Esperado: **4 failed.** Los valores esperados salen redondeados a 2 decimales — `0.13` en vez de `0.125`, `0.63` en vez de `0.625`, `0.88` en vez de `0.875`.

- [ ] **Step 6: Ampliar la escala en los modelos**

En `backend/app/models/inventario.py`, las tres columnas:

```python
    stock_actual = Column(Numeric(10, 3), nullable=False, server_default=text("0"))
    stock_minimo = Column(Numeric(10, 3), nullable=False, server_default=text("0"))
```

```python
    cantidad = Column(Numeric(10, 3), nullable=False)
```

En `backend/app/models/compra.py:56`:

```python
    cantidad = Column(Numeric(10, 3), nullable=False)
```

`DetalleCompra.costo_unitario` y `subtotal` **no se tocan**: son dinero.

- [ ] **Step 7: Tirar otra vez la BD de test**

La corrida RED la recreó con la escala vieja, y `create_all` no altera tablas existentes.

```bash
docker compose exec -T db psql -U cafeteria -d cafeteria_db \
  -c 'DROP DATABASE IF EXISTS cafeteria_db_test'
```

- [ ] **Step 8: Correr los tests y verificar que pasan**

```bash
docker compose exec api pytest -q \
  tests/test_insumos_api.py::test_stock_admite_3_decimales \
  tests/test_insumos_api.py::test_movimiento_admite_3_decimales \
  tests/test_compras_api.py::test_compra_admite_3_decimales_y_subtotal_cuadra \
  tests/test_recetas_api.py::test_consumo_receta_3_decimales_exacto
```

Esperado: **4 passed.**

- [ ] **Step 9: Correr la suite completa del backend**

```bash
docker compose exec api pytest -q
```

Esperado: **221 passed** (217 previos + 4 nuevos), 0 failed.

- [ ] **Step 10: Escribir la migración**

Crea `backend/alembic/versions/7f3a9c2b1d84_inventario_3_decimales.py`:

```python
"""inventario a 3 decimales

Revision ID: 7f3a9c2b1d84
Revises: a1557e1dd3bf
Create Date: 2026-08-09

Amplía las cuatro columnas de cantidad del inventario de Numeric(10,2) a
Numeric(10,3), para que el stock y el kárdex representen exactamente lo que
consume una receta (`producto_insumo.cantidad_requerida` siempre fue (10,3)).
El dinero se queda en 2 decimales.

OJO 1 — detalle_compra.subtotal es una columna GENERADA que depende de
`cantidad`, y Postgres rechaza alterar el tipo de una columna de la que
depende una generada ("cannot alter type of a column used by a generated
column"). Hay que eliminarla, alterar `cantidad` y volver a crearla; Postgres
recalcula la columna generada para las filas existentes, así que no se pierde
nada.

OJO 2 — el downgrade REDONDEA el tercer decimal y esa pérdida es
irreversible: un stock de 0.125 vuelve como 0.13.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7f3a9c2b1d84"
down_revision: Union[str, Sequence[str], None] = "a1557e1dd3bf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_GEN_SUBTOTAL = "cantidad * costo_unitario"


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "insumos", "stock_actual",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "insumos", "stock_minimo",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "movimientos_inventario", "cantidad",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False,
    )
    # detalle_compra: la columna generada bloquea el ALTER, hay que recrearla.
    op.drop_column("detalle_compra", "subtotal")
    op.alter_column(
        "detalle_compra", "cantidad",
        existing_type=sa.Numeric(10, 2), type_=sa.Numeric(10, 3),
        existing_nullable=False,
    )
    op.add_column(
        "detalle_compra",
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            sa.Computed(_GEN_SUBTOTAL, persisted=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema. PIERDE el tercer decimal por redondeo."""
    op.drop_column("detalle_compra", "subtotal")
    op.alter_column(
        "detalle_compra", "cantidad",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False,
    )
    op.add_column(
        "detalle_compra",
        sa.Column(
            "subtotal",
            sa.Numeric(12, 2),
            sa.Computed(_GEN_SUBTOTAL, persisted=True),
            nullable=True,
        ),
    )
    op.alter_column(
        "movimientos_inventario", "cantidad",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False,
    )
    op.alter_column(
        "insumos", "stock_minimo",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
    op.alter_column(
        "insumos", "stock_actual",
        existing_type=sa.Numeric(10, 3), type_=sa.Numeric(10, 2),
        existing_nullable=False, existing_server_default=sa.text("0"),
    )
```

- [ ] **Step 11: Aplicar la migración a la BD de desarrollo y verificar la escala**

```bash
docker compose exec api alembic upgrade head
docker compose exec -T db psql -U cafeteria -d cafeteria_db -c "
SELECT table_name, column_name, numeric_scale
FROM information_schema.columns
WHERE (table_name, column_name) IN
      (('insumos','stock_actual'), ('insumos','stock_minimo'),
       ('movimientos_inventario','cantidad'), ('detalle_compra','cantidad'),
       ('detalle_compra','subtotal'))
ORDER BY table_name, column_name;"
```

Esperado: las cuatro cantidades con `numeric_scale = 3` y `detalle_compra.subtotal` con `numeric_scale = 2`.

- [ ] **Step 12: Verificar que el downgrade corre sin romperse, y volver a subir**

```bash
docker compose exec api alembic downgrade -1
docker compose exec api alembic upgrade head
```

Esperado: ambos comandos terminan sin error. (El downgrade redondea datos — por eso se vuelve a subir de inmediato; los datos demo son reemplazables por el seed.)

- [ ] **Step 13: Verificar que la columna generada sigue viva tras el ida y vuelta**

```bash
docker compose exec -T db psql -U cafeteria -d cafeteria_db -c "
SELECT is_generated, generation_expression FROM information_schema.columns
WHERE table_name='detalle_compra' AND column_name='subtotal';"
```

Esperado: `ALWAYS` y `(cantidad * costo_unitario)`.

- [ ] **Step 14: Commit**

```bash
git add backend/app/models/inventario.py backend/app/models/compra.py \
        backend/alembic/versions/7f3a9c2b1d84_inventario_3_decimales.py \
        backend/tests/test_insumos_api.py backend/tests/test_compras_api.py \
        backend/tests/test_recetas_api.py
git commit -m "feat(api): inventario y kárdex a 3 decimales

Las cuatro columnas de cantidad pasan de Numeric(10,2) a Numeric(10,3) para
que el stock represente exactamente lo que consume una receta
(cantidad_requerida siempre fue (10,3)). El dinero se queda en 2 decimales.

La migración elimina y recrea detalle_compra.subtotal: es una columna generada
que depende de cantidad y Postgres rechaza el ALTER mientras exista."
```

---

## Task 2: Validación de 3 decimales en Pydantic (422)

Hoy ningún schema limita decimales y Postgres redondea en silencio. Esta tarea hace explícito el rechazo.

**Files:**
- Modify: `backend/app/schemas/insumo.py:18-19,26,33`
- Modify: `backend/app/schemas/compra.py:26`
- Modify: `backend/app/schemas/receta.py:8,12`
- Test: `backend/tests/test_insumos_api.py`, `backend/tests/test_compras_api.py`, `backend/tests/test_recetas_api.py`

**Interfaces:**
- Consumes: columnas con escala 3 de la Tarea 1.
- Produces: la API responde 422 ante cantidades con 4+ decimales. Las Tareas 3 y 4 (móvil) validan del lado del cliente para que ese 422 no llegue nunca en uso normal.

- [ ] **Step 1: Escribir los tests que fallan**

Añade al final de `backend/tests/test_insumos_api.py`:

```python
def test_stock_4_decimales_422(client, db, cocinero_headers):
    """Redondear en silencio descuadra el kárdex sin que nadie se entere: la API
    prefiere rechazar y que el cliente corrija."""
    r = _crear_insumo(
        client, db, cocinero_headers, nombre="Azafrán", stock="0.1234"
    )
    assert r.status_code == 422


def test_stock_minimo_4_decimales_patch_422(client, db, cocinero_headers):
    insumo = _crear_insumo(client, db, cocinero_headers, nombre="Comino").json()
    r = client.patch(
        f"/api/v1/insumos/{insumo['id_insumo']}",
        headers=cocinero_headers,
        json={"stock_minimo": "1.0005"},
    )
    assert r.status_code == 422


def test_movimiento_4_decimales_422(client, db, cocinero_headers):
    insumo = _crear_insumo(
        client, db, cocinero_headers, nombre="Pimienta", stock="10.000"
    ).json()
    r = _movimiento(
        client, cocinero_headers, insumo["id_insumo"], "Salida", "Merma", "0.1234"
    )
    assert r.status_code == 422
```

Añade al final de `backend/tests/test_compras_api.py`:

```python
def test_compra_cantidad_4_decimales_422(client, db, cocinero_headers):
    prov = _proveedor_id(client, cocinero_headers, "Granos Finos")
    ins = _insumo(client, db, cocinero_headers, nombre="Anís")
    r = client.post(
        "/api/v1/compras",
        headers=cocinero_headers,
        json={
            "id_proveedor": prov,
            "items": [
                {
                    "id_insumo": ins["id_insumo"],
                    "cantidad": "0.1234",
                    "costo_unitario": "10.00",
                }
            ],
        },
    )
    assert r.status_code == 422
```

Añade al final de `backend/tests/test_recetas_api.py`:

```python
def test_receta_cantidad_4_decimales_422(client, db, admin_headers, cocinero_headers):
    pid = _producto_id(client, db, admin_headers, nombre="Té especiado")
    iid = _insumo_id(client, db, cocinero_headers, nombre="Jengibre")
    r = client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=cocinero_headers,
        json={"id_insumo": iid, "cantidad_requerida": "0.1234"},
    )
    assert r.status_code == 422
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

```bash
docker compose exec api pytest -q \
  tests/test_insumos_api.py::test_stock_4_decimales_422 \
  tests/test_insumos_api.py::test_stock_minimo_4_decimales_patch_422 \
  tests/test_insumos_api.py::test_movimiento_4_decimales_422 \
  tests/test_compras_api.py::test_compra_cantidad_4_decimales_422 \
  tests/test_recetas_api.py::test_receta_cantidad_4_decimales_422
```

Esperado: **5 failed** — devuelven 200/201 porque hoy la BD redondea sin protestar.

- [ ] **Step 3: Añadir la validación en los tres schemas**

En `backend/app/schemas/insumo.py`, las cuatro cantidades. `max_digits=10` con `decimal_places=3` deja el tope en 9 999 999.999, exactamente lo que aguanta la columna:

```python
class InsumoCreate(BaseModel):
    nombre_insumo: str = Field(min_length=1)
    id_unidad: int
    descripcion: str | None = None
    stock_actual: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=3)
    stock_minimo: Decimal = Field(default=Decimal("0"), ge=0, max_digits=10, decimal_places=3)
    costo_unitario: Decimal = Field(default=Decimal("0"), ge=0)


class InsumoUpdate(BaseModel):
    nombre_insumo: str | None = None
    descripcion: str | None = None
    stock_minimo: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=3)
    costo_unitario: Decimal | None = Field(default=None, ge=0)


class MovimientoCreate(BaseModel):
    tipo: str
    motivo: str
    cantidad: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
```

`costo_unitario` queda intacto a propósito: es dinero.

En `backend/app/schemas/compra.py:24-27`:

```python
class CompraItemIn(BaseModel):
    id_insumo: int
    cantidad: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
    costo_unitario: Decimal = Field(ge=0)
```

En `backend/app/schemas/receta.py`, las dos clases de entrada (`RecetaLineaCreate` y `RecetaLineaUpdate`):

```python
    cantidad_requerida: Decimal = Field(gt=0, max_digits=10, decimal_places=3)
```

`RecetaLineaOut.cantidad_requerida` **no** cambia: los schemas de salida solo declaran el tipo.

- [ ] **Step 4: Correr los tests y verificar que pasan**

```bash
docker compose exec api pytest -q \
  tests/test_insumos_api.py::test_stock_4_decimales_422 \
  tests/test_insumos_api.py::test_stock_minimo_4_decimales_patch_422 \
  tests/test_insumos_api.py::test_movimiento_4_decimales_422 \
  tests/test_compras_api.py::test_compra_cantidad_4_decimales_422 \
  tests/test_recetas_api.py::test_receta_cantidad_4_decimales_422
```

Esperado: **5 passed.**

- [ ] **Step 5: Correr la suite completa y vigilar las regresiones**

```bash
docker compose exec api pytest -q
```

Esperado: **226 passed**, 0 failed. Vigila en particular `test_seed_demo.py` y los tests de compras/recetas que mandan cantidades como float JSON: si alguno empieza a fallar con 422, es porque un float como `0.1` llegó a `Decimal` con más de 3 decimales. En ese caso pásalo a string en el test (`"0.1"`), no relajes la validación.

- [ ] **Step 6: Commit**

```bash
git add backend/app/schemas/insumo.py backend/app/schemas/compra.py \
        backend/app/schemas/receta.py backend/tests/test_insumos_api.py \
        backend/tests/test_compras_api.py backend/tests/test_recetas_api.py
git commit -m "feat(api): rechazar con 422 las cantidades de más de 3 decimales

Antes Postgres redondeaba en silencio y el usuario nunca sabía que su número
había cambiado. La validación vive en el borde (Pydantic) y la columna queda
como red de seguridad. Los campos de dinero no se tocan."
```

---

## Task 3: Móvil — validación decimal compartida

Un solo lugar para el regex, tres consumidores. De paso, la pantalla de Ajuste y la de Compra nueva pasan a aceptar coma decimal, que hoy solo funciona en Recetas.

**Files:**
- Create: `mobile/src/lib/decimales.ts`
- Create: `mobile/src/lib/decimales.test.ts`
- Modify: `mobile/src/lib/recetas.ts:1-19`
- Modify: `mobile/src/lib/inventario.ts:8-14`
- Modify: `mobile/src/lib/compras.ts:1-12`
- Modify: `mobile/src/app/cocina/ajuste.tsx:56`
- Modify: `mobile/src/app/cocina/compra-nueva.tsx:78`
- Test: `mobile/src/lib/recetas.test.ts`, `inventario.test.ts`, `compras.test.ts`

**Interfaces:**
- Consumes: el 422 de la Tarea 2 (la validación del cliente existe para evitarlo).
- Produces:
  - `normalizar(txt: string): string` — coma → punto, con trim.
  - `decimalesValidos(txt: string, max: number): boolean` — número > 0 con hasta `max` decimales.
  - `aCantidad(txt: string): number` — normaliza y convierte.
  Los tres se exportan desde `mobile/src/lib/decimales.ts`. `aCantidad` se sigue re-exportando desde `recetas.ts` para no romper a sus consumidores actuales.

- [ ] **Step 1: Escribir el test que falla del módulo nuevo**

Crea `mobile/src/lib/decimales.test.ts`:

```typescript
import { aCantidad, decimalesValidos, normalizar } from "./decimales";

test("normalizar convierte la coma decimal en punto y recorta espacios", () => {
  expect(normalizar(" 0,25 ")).toBe("0.25");
  expect(normalizar("0.25")).toBe("0.25");
});

test("decimalesValidos exige número > 0 con hasta N decimales", () => {
  expect(decimalesValidos("2", 3)).toBe(true);
  expect(decimalesValidos("0.125", 3)).toBe(true);
  expect(decimalesValidos("0,125", 3)).toBe(true);
  expect(decimalesValidos("0.1255", 3)).toBe(false);
  expect(decimalesValidos("0.125", 2)).toBe(false);
  expect(decimalesValidos("0", 3)).toBe(false);
  expect(decimalesValidos("-1", 3)).toBe(false);
  expect(decimalesValidos("", 3)).toBe(false);
  expect(decimalesValidos("abc", 3)).toBe(false);
});

test("aCantidad normaliza la coma decimal a punto", () => {
  expect(aCantidad("0,125")).toBe(0.125);
  expect(aCantidad("3")).toBe(3);
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

```bash
cd mobile && npx jest src/lib/decimales.test.ts
```

Esperado: FAIL — `Cannot find module './decimales'`.

- [ ] **Step 3: Crear el módulo**

Crea `mobile/src/lib/decimales.ts`:

```typescript
/**
 * Reglas decimales compartidas por inventario, compras y recetas.
 *
 * La API acepta cantidades con hasta 3 decimales y rechaza el resto con 422
 * (Numeric(10,3) en insumos, kárdex, detalle de compra y recetas). Validar aquí
 * evita que ese 422 le llegue al usuario en forma de error de red.
 */

/** Normaliza la coma decimal a punto: los teclados numéricos varían por locale. */
export function normalizar(txt: string): string {
  return txt.trim().replace(",", ".");
}

/** Número > 0 con hasta `max` decimales, aceptando coma o punto. */
export function decimalesValidos(txt: string, max: number): boolean {
  const t = normalizar(txt);
  const re = new RegExp(`^\\d+(\\.\\d{1,${max}})?$`);
  if (!re.test(t)) return false;
  return Number(t) > 0;
}

export function aCantidad(txt: string): number {
  return Number(normalizar(txt));
}
```

- [ ] **Step 4: Correr el test y verificar que pasa**

```bash
cd mobile && npx jest src/lib/decimales.test.ts
```

Esperado: **3 passed.**

- [ ] **Step 5: Actualizar los tests de los tres consumidores**

En `mobile/src/lib/recetas.test.ts`, reemplaza el test de `cantidadValida` (líneas 8-18) — ahora 3 decimales son válidos:

```typescript
test("cantidadValida exige número > 0 con hasta 3 decimales", () => {
  expect(cantidadValida("2")).toBe(true);
  expect(cantidadValida("0.25")).toBe(true);
  expect(cantidadValida("0,25")).toBe(true);
  expect(cantidadValida("0.125")).toBe(true);
  expect(cantidadValida("0.1255")).toBe(false);
  expect(cantidadValida("0")).toBe(false);
  expect(cantidadValida("-1")).toBe(false);
  expect(cantidadValida("")).toBe(false);
  expect(cantidadValida("abc")).toBe(false);
});
```

En `mobile/src/lib/inventario.test.ts`, reemplaza el test de `movimientoValido` (líneas 9-15):

```typescript
test("movimientoValido exige tipo, motivo y cantidad > 0 de hasta 3 decimales", () => {
  expect(movimientoValido("Salida", "Merma", "2")).toBe(true);
  expect(movimientoValido("Salida", "Merma", "0.125")).toBe(true);
  expect(movimientoValido("Salida", "Merma", "0,125")).toBe(true);
  expect(movimientoValido("Salida", "Merma", "0.1255")).toBe(false);
  expect(movimientoValido(null, "Merma", "2")).toBe(false);
  expect(movimientoValido("Salida", null, "2")).toBe(false);
  expect(movimientoValido("Salida", "Merma", "0")).toBe(false);
  expect(movimientoValido("Salida", "Merma", "")).toBe(false);
});
```

En `mobile/src/lib/compras.test.ts`, reemplaza el test de `lineaCompraValida` (líneas 3-9):

```typescript
test("lineaCompraValida exige insumo, cantidad > 0 de hasta 3 decimales y costo >= 0 no vacío", () => {
  expect(lineaCompraValida(1, "2", "30")).toBe(true);
  expect(lineaCompraValida(1, "0.125", "30")).toBe(true);
  expect(lineaCompraValida(1, "2", "0")).toBe(true);
  expect(lineaCompraValida(1, "0.1255", "30")).toBe(false);
  expect(lineaCompraValida(null, "2", "30")).toBe(false);
  expect(lineaCompraValida(1, "0", "30")).toBe(false);
  expect(lineaCompraValida(1, "2", "")).toBe(false);
});
```

- [ ] **Step 6: Correr los tests y verificar que fallan**

```bash
cd mobile && npx jest src/lib/recetas.test.ts src/lib/inventario.test.ts src/lib/compras.test.ts
```

Esperado: **3 suites FAIL** — `cantidadValida("0.125")` da `false` (aún limita a 2) y los dos validadores nuevos aceptan `"0.1255"` (aún no miran decimales).

- [ ] **Step 7: Reescribir los tres consumidores sobre el helper**

`mobile/src/lib/recetas.ts` — elimina `normalizar` y `aCantidad` locales, reexporta `aCantidad` y reescribe `cantidadValida`:

```typescript
import { decimalesValidos } from "./decimales";

export { aCantidad } from "./decimales";

/**
 * Cantidad de receta válida: número > 0 con hasta 3 decimales, lo mismo que
 * aceptan el inventario y el kárdex desde la migración a Numeric(10,3).
 */
export function cantidadValida(txt: string): boolean {
  return decimalesValidos(txt, 3);
}
```

El resto del archivo (`plano`, `filtrarProductos`, `insumosDisponibles`) queda igual. `plano` no dependía de `normalizar`.

`mobile/src/lib/inventario.ts`:

```typescript
import { decimalesValidos } from "./decimales";

export function stockBajo(insumo: {
  stock_actual: number;
  stock_minimo: number;
}): boolean {
  return insumo.stock_actual <= insumo.stock_minimo;
}

export function movimientoValido(
  tipo: string | null,
  motivo: string | null,
  cantidadTxt: string
): boolean {
  return tipo !== null && motivo !== null && decimalesValidos(cantidadTxt, 3);
}
```

`mobile/src/lib/compras.ts` — solo la primera función; `compraTotal` y `compraValida` no cambian:

```typescript
import { decimalesValidos } from "./decimales";

export function lineaCompraValida(
  idInsumo: number | null,
  cantidadTxt: string,
  costoTxt: string
): boolean {
  return (
    idInsumo !== null &&
    decimalesValidos(cantidadTxt, 3) &&
    costoTxt !== "" &&
    Number(costoTxt) >= 0
  );
}
```

- [ ] **Step 8: Hacer que las dos pantallas manden la cantidad normalizada**

`decimalesValidos` acepta coma, así que ahora el usuario puede escribir `0,125` en Ajuste y en Compra nueva; si la pantalla sigue mandando `Number(cantidadTxt)` enviaría `NaN`. Cambia ambas a `aCantidad`.

En `mobile/src/app/cocina/ajuste.tsx`, añade el import y cambia la línea 56:

```typescript
import { aCantidad } from "@/lib/decimales";
```

```typescript
        cantidad: aCantidad(cantidadTxt),
```

En `mobile/src/app/cocina/compra-nueva.tsx`, añade el import y cambia la línea 78:

```typescript
import { aCantidad } from "@/lib/decimales";
```

```typescript
        cantidad: aCantidad(cantidadTxt),
```

- [ ] **Step 9: Correr los tests y el chequeo de tipos**

```bash
cd mobile && npx jest src/lib/ && npx tsc --noEmit
```

Esperado: todas las suites de `src/lib` en verde y `tsc` sin salida.

- [ ] **Step 10: Correr la suite móvil completa**

```bash
cd mobile && npm test
```

Esperado: **82 passed** (79 previos + 3 del módulo nuevo), 0 failed.

- [ ] **Step 11: Commit**

```bash
git add mobile/src/lib/decimales.ts mobile/src/lib/decimales.test.ts \
        mobile/src/lib/recetas.ts mobile/src/lib/recetas.test.ts \
        mobile/src/lib/inventario.ts mobile/src/lib/inventario.test.ts \
        mobile/src/lib/compras.ts mobile/src/lib/compras.test.ts \
        mobile/src/app/cocina/ajuste.tsx mobile/src/app/cocina/compra-nueva.tsx
git commit -m "feat(mobile): validación decimal compartida a 3 decimales

Un solo regex en lib/decimales.ts para recetas, ajustes de inventario y líneas
de compra. Recetas sube de 2 a 3 decimales (el límite existía para no
desincronizar el kárdex, ya no hace falta) y las otras dos pasan a validar
decimales en vez de solo exigir > 0, para que el 422 nuevo de la API no llegue
como error de red. Ajuste y Compra nueva aceptan coma decimal."
```

---

## Task 4: Móvil — helper `cantidad()` para el despliegue

`coerce.ts` ya convierte `"500.000"` a `500`, así que las pantallas hoy muestran bien las cantidades **por accidente**. Esta tarea lo convierte en una convención con nombre, igual que `money()`.

**Files:**
- Modify: `mobile/src/lib/format.ts`
- Modify: `mobile/src/lib/format.test.ts`
- Modify: `mobile/src/app/cocina/inventario.tsx:75,80`
- Modify: `mobile/src/app/cocina/ajuste.tsx:62,105`
- Modify: `mobile/src/app/cocina/receta-detalle.tsx:222`
- Modify: `mobile/src/app/cocina/compra-nueva.tsx:198`

**Interfaces:**
- Consumes: nada de tareas previas (independiente de la Tarea 3).
- Produces: `cantidad(value: number | string | null | undefined): string` en `mobile/src/lib/format.ts`.

- [ ] **Step 1: Escribir el test que falla**

Añade al final de `mobile/src/lib/format.test.ts`:

```typescript
import { cantidad, money } from "./format";

test("cantidad muestra hasta 3 decimales sin ceros de relleno", () => {
  expect(cantidad(500)).toBe("500");
  expect(cantidad(12.5)).toBe("12.5");
  expect(cantidad(0.125)).toBe("0.125");
  // La API serializa Decimal como string: "500.000" no debe mostrarse tal cual
  expect(cantidad("500.000")).toBe("500");
  expect(cantidad("0.125")).toBe("0.125");
});

test("cantidad recorta el cuarto decimal y tolera null/undefined", () => {
  expect(cantidad(0.1234)).toBe("0.123");
  expect(cantidad(null)).toBe("0");
  expect(cantidad(undefined)).toBe("0");
});
```

Actualiza la línea 1 del archivo para importar ambas funciones (el `import { money } from "./format";` original se reemplaza por el import conjunto de arriba).

- [ ] **Step 2: Correr el test y verificar que falla**

```bash
cd mobile && npx jest src/lib/format.test.ts
```

Esperado: FAIL — `cantidad is not a function`.

- [ ] **Step 3: Implementar el helper**

Añade al final de `mobile/src/lib/format.ts`:

```typescript
/**
 * Formatea una cantidad de inventario: hasta 3 decimales, sin ceros de relleno.
 *
 * La API manda las cantidades como string con la escala completa ("500.000"),
 * y `coerceDecimals` las convierte a number en el borde del cliente. Este
 * helper fija la regla de presentación en un solo sitio: "500", "12.5",
 * "0.125" — nunca "500.000" ni un `.toFixed(2)` que se coma el tercer decimal.
 */
export function cantidad(value: number | string | null | undefined): string {
  return String(Number(Number(value ?? 0).toFixed(3)));
}
```

`toFixed(3)` recorta el cuarto decimal y `Number(...)` elimina los ceros de relleno; el `String` final evita la notación exponencial que `toString` solo usaría con números mucho más grandes que los de este dominio.

- [ ] **Step 4: Correr el test y verificar que pasa**

```bash
cd mobile && npx jest src/lib/format.test.ts
```

Esperado: **4 passed** (los 2 de `money` + los 2 nuevos).

- [ ] **Step 5: Usar el helper en las cuatro pantallas**

`mobile/src/app/cocina/inventario.tsx` — importa `cantidad` desde `@/lib/format` y cambia las dos líneas de despliegue:

```tsx
                <Text style={styles.meta}>
                  mín. {cantidad(item.stock_minimo)} {item.unidad.abreviatura}
                </Text>
```

```tsx
                <Text style={[styles.stock, bajo && styles.stockBajoTxt]}>
                  {cantidad(item.stock_actual)} {item.unidad.abreviatura}
                </Text>
```

`mobile/src/app/cocina/ajuste.tsx` — importa `cantidad` y cambia el alert y el encabezado:

```tsx
      Alert.alert(
        "Listo",
        `Stock actualizado: ${cantidad(actualizado.stock_actual)} ${actualizado.unidad.abreviatura}`
      );
```

```tsx
      <Text style={styles.stock}>
        Stock: {cantidad(insumo.stock_actual)} {insumo.unidad.abreviatura}
      </Text>
```

`mobile/src/app/cocina/receta-detalle.tsx` — importa `cantidad` y cambia la línea 222:

```tsx
                    <Text style={styles.cantidad}>
                      {cantidad(item.cantidad_requerida)} {item.insumo.unidad.abreviatura}
                    </Text>
```

La línea 218 (`setEditTxt(String(item.cantidad_requerida))`) **no cambia**: alimenta un campo editable, no una etiqueta.

`mobile/src/app/cocina/compra-nueva.tsx` — importa `cantidad` y cambia la línea 198:

```tsx
            <Text style={styles.rowL}>
              {cantidad(l.cantidad)} × {l.nombre}
            </Text>
```

El importe de la línea siguiente (`(l.cantidad * l.costo_unitario).toFixed(2)`) **no cambia**: es dinero.

- [ ] **Step 6: Verificar tipos y suite completa**

```bash
cd mobile && npx tsc --noEmit && npm test
```

Esperado: `tsc` sin salida; **84 passed**, 0 failed.

- [ ] **Step 7: Commit**

```bash
git add mobile/src/lib/format.ts mobile/src/lib/format.test.ts \
        mobile/src/app/cocina/inventario.tsx mobile/src/app/cocina/ajuste.tsx \
        mobile/src/app/cocina/receta-detalle.tsx mobile/src/app/cocina/compra-nueva.tsx
git commit -m "feat(mobile): helper cantidad() para mostrar cantidades sin ceros de relleno

coerceDecimals ya convertía \"500.000\" a 500, así que las pantallas mostraban
bien las cantidades por accidente. El helper fija la regla en un solo sitio,
junto a money(), y protege el tercer decimal de un .toFixed(2) futuro."
```

---

## Task 5: Panel web — cantidades con 3 decimales en el reporte

`_fmt_cell` formatea **todo** `float` con `.2f`, así que sin esta tarea un stock de `0.125` se vería como `0.13` en la vista previa y en el PDF: justo donde el administrador consulta el inventario.

**Files:**
- Modify: `web/app/reportes/routes.py:30-43,79-84`
- Test: `web/tests/test_reportes.py`

**Interfaces:**
- Consumes: el reporte de inventario de la API, que ya devuelve `stock_actual`/`stock_minimo` como Decimal-string con escala 3 tras la Tarea 1.
- Produces: `Cantidad(float)` y `_cantidad(v) -> Cantidad` en `web/app/reportes/routes.py`.

- [ ] **Step 1: Escribir los tests que fallan**

Añade al final de `web/tests/test_reportes.py`:

```python
def test_fmt_cell_cantidad_sin_ceros_de_relleno():
    """Las cantidades se muestran con hasta 3 decimales y sin relleno; el dinero
    (float normal) sigue con dos, que es la regla vieja y no debe romperse."""
    from app.reportes.routes import _cantidad, _fmt_cell

    assert _fmt_cell(_cantidad("500.000")) == "500"
    assert _fmt_cell(_cantidad("12.500")) == "12.5"
    assert _fmt_cell(_cantidad("0.125")) == "0.125"
    assert _fmt_cell(_cantidad("0.000")) == "0"
    assert _fmt_cell(1234.5) == "1234.50"


def test_cantidad_es_float_para_el_xlsx():
    """openpyxl decide con isinstance: si Cantidad dejara de ser float, el XLSX
    escribiría las cantidades como texto y se perderían SUM/orden/filtro."""
    from app.reportes.routes import _cantidad

    assert isinstance(_cantidad("0.125"), float)


def test_reportes_preview_inventario_3_decimales(client, monkeypatch):
    _login(client, monkeypatch)
    _stub(monkeypatch)
    monkeypatch.setattr(
        api_client,
        "get_inventario_niveles",
        lambda a, solo_bajo_minimo=False: [
            {"nombre": "Canela", "unidad": "kg", "stock_actual": "0.125",
             "stock_minimo": "0.500", "nivel_pct": 12, "bajo_minimo": True}
        ],
    )
    cuerpo = client.get("/reportes?tipo=inventario").get_data(as_text=True)
    assert "0.125" in cuerpo
    assert "0.5" in cuerpo
    assert "0.13" not in cuerpo
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

El contenedor `web` monta `./web` en `/code`, así que dentro la ruta es `tests/…`, sin el prefijo `web/`:

```bash
docker compose exec web pytest -q \
  tests/test_reportes.py::test_fmt_cell_cantidad_sin_ceros_de_relleno \
  tests/test_reportes.py::test_cantidad_es_float_para_el_xlsx \
  tests/test_reportes.py::test_reportes_preview_inventario_3_decimales
```

Esperado: **3 failed** — los dos primeros con `ImportError` (`_cantidad` no existe) y el tercero porque el cuerpo trae `0.13`.

- [ ] **Step 3: Añadir el tipo marcador y el constructor**

En `web/app/reportes/routes.py`, justo después de `TIPOS = (...)` (línea 11):

```python
class Cantidad(float):
    """Marca una celda como cantidad de inventario (hasta 3 decimales).

    Es subclase de `float` a propósito: openpyxl decide con `isinstance`, así
    que el XLSX la sigue escribiendo como celda numérica (SUM/orden/filtro en
    Excel). `_fmt_cell` la intercepta para las salidas de texto (HTML y PDF) y
    la formatea sin los ceros de relleno que impone el `.2f` del dinero.
    """


def _cantidad(v) -> Cantidad:
    return Cantidad(round(float(v), 3))
```

- [ ] **Step 4: Formatear la cantidad en `_fmt_cell`**

Reemplaza `_fmt_cell` (líneas 79-84). La rama de `Cantidad` va **antes** que la de `float`, porque `isinstance(Cantidad(...), float)` también es cierto:

```python
def _fmt_cell(v):
    if v is None:
        return ""
    if isinstance(v, Cantidad):
        return f"{v:.3f}".rstrip("0").rstrip(".")
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)
```

- [ ] **Step 5: Usar `_cantidad` en la fila de inventario**

En el bloque `if tipo == "inventario":` (líneas 30-43), cambia las dos celdas de stock:

```python
                _cantidad(f["stock_actual"]),
                _cantidad(f["stock_minimo"]),
```

`nivel_pct` sigue con `int(...)` y las columnas de texto no cambian.

- [ ] **Step 6: Correr los tests y verificar que pasan**

```bash
docker compose exec web pytest -q \
  tests/test_reportes.py::test_fmt_cell_cantidad_sin_ceros_de_relleno \
  tests/test_reportes.py::test_cantidad_es_float_para_el_xlsx \
  tests/test_reportes.py::test_reportes_preview_inventario_3_decimales
```

Esperado: **3 passed.**

- [ ] **Step 7: Correr la suite web completa**

```bash
docker compose exec web pytest -q
```

Esperado: **123 passed** (120 previos + 3 nuevos), 0 failed. El test viejo `test_reportes_preview_inventario` sigue verde: su stub tiene `"5.00"`, que ahora se muestra como `5` — el test solo busca `"Café"` y el título, no el número.

- [ ] **Step 8: Commit**

```bash
git add web/app/reportes/routes.py web/tests/test_reportes.py
git commit -m "feat(web): cantidades del reporte de inventario con 3 decimales

_fmt_cell formateaba todo float con .2f, así que un stock de 0.125 se veía
como 0.13 en la vista previa y en el PDF. El tipo marcador Cantidad(float) se
formatea sin ceros de relleno y, por ser subclase de float, openpyxl lo sigue
escribiendo como celda numérica en el XLSX."
```

---

## Task 6: Documentación

**Files:**
- Modify: `README.md` — el paso de la migración junto al seed.
- Modify: `progress.md` — sección "Próximo" y "Deuda técnica".
- Modify: `CONTEXTO-PROYECTO.md` — la nota de recetas a 2 decimales (línea 124) y la lista de migraciones (línea 70).

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: nada de código.

- [ ] **Step 1: Documentar el paso de migración en el README**

En la sección de arranque del `README.md`, junto al `python -m app.db.seed`, añade el comando y su motivo:

```bash
docker compose exec api alembic upgrade head   # esquema al día (migraciones)
```

Con una línea de contexto debajo: el stack no aplica migraciones al arrancar, así que después de un `git pull` que traiga una revisión nueva hay que correrlo a mano.

- [ ] **Step 2: Actualizar `progress.md`**

- Cabecera "Última actualización" a la fecha del merge.
- En "Próximo": reemplazar la línea de candidato siguiente por el estado de este slice, con los conteos de la suite (backend 226, web 123, móvil 84) y el recordatorio de `alembic upgrade head` al desplegar.
- En "Deuda técnica": **eliminar** la línea 146 (`Inventario a 2 decimales vs. cantidad_requerida a 3`), que este slice cierra. Añadir en su lugar las dos deudas nuevas que deja la spec: los campos de dinero siguen sin `decimal_places=2` en Pydantic (mismo redondeo silencioso, otro radio de impacto), y el `downgrade` de la migración redondea el tercer decimal.

- [ ] **Step 3: Actualizar `CONTEXTO-PROYECTO.md`**

- Línea 70: la lista de migraciones ya no es "migración única"; añadir la revisión `7f3a9c2b1d84` y qué hace.
- Línea 124: la nota de Recetas dice que la cantidad se captura con 2 decimales porque el inventario es `Numeric(10,2)`. Reescribirla: ahora son 3 decimales en toda la cadena (receta, stock, kárdex y detalle de compra), con validación 422 en la API.
- Actualizar los conteos de tests y la lista de PRs.

- [ ] **Step 4: Verificar que no queda ninguna referencia al límite viejo**

```bash
grep -rn "2 decimales" README.md progress.md CONTEXTO-PROYECTO.md mobile/src backend/app web/app
```

Esperado: solo aciertos sobre **dinero** (importes, precios, `money()`). Cualquier acierto que hable de cantidades, stock, kárdex o recetas es documentación desactualizada — corrígela.

- [ ] **Step 5: Commit**

```bash
git add README.md progress.md CONTEXTO-PROYECTO.md
git commit -m "docs: inventario a 3 decimales — paso de migración y cierre de la deuda

El README documenta que el esquema se actualiza a mano (el stack no corre
alembic al arrancar). progress.md cierra la deuda del inventario a 2 decimales
y anota las dos que deja este slice: el dinero sin decimal_places y el
downgrade que redondea."
```

---

## Verificación final antes del PR

- [ ] **Suite completa de las tres capas**

```bash
docker compose exec api pytest -q      # esperado: 226 passed
docker compose exec web pytest -q      # esperado: 123 passed
cd mobile && npm test                  # esperado: 84 passed
cd mobile && npx tsc --noEmit          # esperado: sin salida
```

- [ ] **Migración aplicada sobre la BD real y escala verificada**

```bash
docker compose exec api alembic upgrade head
docker compose exec -T db psql -U cafeteria -d cafeteria_db -c "
SELECT table_name, column_name, numeric_scale FROM information_schema.columns
WHERE (table_name, column_name) IN
      (('insumos','stock_actual'), ('insumos','stock_minimo'),
       ('movimientos_inventario','cantidad'), ('detalle_compra','cantidad'))
ORDER BY table_name;"
```

- [ ] **Verificación manual del usuario** (él abre la app y revisa; Claude no mergea)

1. Alta de un insumo con stock `0.125` — se guarda y se muestra `0.125`, no `0.13`.
2. Ajuste de `0.005` sobre ese insumo — stock resultante `0.13`.
3. Compra con cantidad fraccionaria — el kárdex registra la cantidad exacta y el subtotal cuadra.
4. Receta con `0.125` de un insumo, pedido con 3 unidades: el descuento al crear el pedido es exacto.
5. Reporte de Inventario en el panel: vista previa, PDF y XLSX con las cantidades recortadas.
6. Intentar capturar 4 decimales en el móvil: el botón queda deshabilitado, no llega un error de red.
