# Cuenta por mesa (venta multi-pedido) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cobrar todas las rondas de una mesa en una sola venta (un folio, un ticket, un juego de pagos), conservando el cobro de ronda suelta.

**Architecture:** Se invierte la FK venta↔pedido: `ventas.id_pedido` desaparece y `pedidos.id_venta` (nullable) toma su lugar — una venta cubre N pedidos de la misma mesa. `POST /ventas` acepta `ids_pedidos`; con más de un pedido exige todos Entregados. En el móvil, Caja agrupa los pedidos por mesa (helper puro `agruparPorMesa`) y la pantalla de cobro opera sobre la unión de líneas de N pedidos — la calculadora de división (`lib/split.ts`) no cambia.

**Tech Stack:** FastAPI + SQLAlchemy + Alembic (backend), Expo/React Native + Jest (móvil). Web sin cambios.

**Spec:** `docs/superpowers/specs/2026-08-11-cuenta-por-mesa-design.md`

## Global Constraints

- **Idioma:** comentarios, mensajes de error y commits en español. **Commits atómicos** por tarea con sus tests.
- **Dinero:** la API serializa Decimal como **string**; en móvil se muestra con `money()` y las sumas se acumulan **en centavos** (`Math.round(n*100)`), nunca con floats directos.
- **Reglas que NO cambian:** cobro de **un** pedido conserva el comportamiento actual (se puede cobrar sin estar Entregado, mismos mensajes 404/409/422); la regla de excedente solo-Efectivo vive en el cliente; el guard de mesa del PR #24 y la liberación condicional del PR #31 se conservan (esta última generalizada a lista).
- **⚠️ NO correr `alembic upgrade head` contra la BD de dev del stack principal** hasta que el PR esté mergeado: el código de `main` aún espera el esquema viejo. La migración se ejercita con el stack del worktree (BD desde cero) y el backfill real se verifica en el ritual post-merge.

## Cómo correr los tests

El suite backend usa `create_all` sobre una BD `_test` autoprovisionada — puede correr contra la BD del **stack principal** (que ya está arriba) sin migrarla. Contenedor efímero montando el worktree; **no omitas `--user`** (pytest deja `__pycache__` de root y luego el worktree no se puede borrar):

```bash
# Backend (usa la red del stack principal; la BD _test es propia del suite)
docker run --rm --network cafeteria-system_default \
  --user $(id -u):$(id -g) \
  --env-file /home/vikca/cafeteria-system/.claude/worktrees/cuenta-mesa/.env \
  -v /home/vikca/cafeteria-system/.claude/worktrees/cuenta-mesa/backend:/code -w /code \
  cafeteria-system-api pytest -q

# Móvil
cd /home/vikca/cafeteria-system/.claude/worktrees/cuenta-mesa/mobile
npm install         # primera vez en el worktree
npm test && npx tsc --noEmit
```

## File Structure

```
backend/alembic/versions/c3d5e7f9a1b2_venta_multipedido.py  (create)  FK invertida + backfill
backend/app/models/venta.py         (edit)  Venta.pedidos (1:N); fuera id_pedido
backend/app/models/pedido.py        (edit)  Pedido.id_venta + relación venta
backend/app/schemas/venta.py        (edit)  VentaCreate.ids_pedidos; VentaOut.ids_pedidos
backend/app/services/pedido_service.py (edit)  condiciones_pedido_activo por id_venta; excepto_ids lista
backend/app/services/venta_service.py  (edit)  cobrar acepta N pedidos; to_out
backend/app/services/reporte_service.py (edit)  joins por Pedido.id_venta
backend/tests/test_ventas_api.py    (edit)  payloads nuevos + tests de cuenta
backend/tests/*                     (edit)  payloads POST /ventas actualizados
mobile/src/api/client.ts            (edit)  cobrarVenta(ids); Venta.ids_pedidos
mobile/src/api/client.test.ts       (edit)  stubs del nuevo shape
mobile/src/lib/caja.ts              (edit)  agruparPorMesa, cuentaCobrable, CuentaMesa
mobile/src/lib/caja.test.ts         (edit)  sus tests
mobile/src/app/caja/index.tsx       (edit)  tarjetas de cuenta por mesa
mobile/src/app/caja/cobro.tsx       (edit)  cobro multi-pedido
mobile/src/lib/ticket.ts            (edit)  ticketHtml(venta, pedidos[])
mobile/src/lib/ticket.test.ts       (edit)  sus tests
```

---

## Tarea 1 — Backend: inversión de la FK y cobro multi-pedido

Es la tarea grande y **atómica por necesidad**: migración, modelos, servicio, schemas y reportes cambian juntos (no hay estado intermedio con la suite en verde). El TDD va por los tests de API.

**Files:**
- Create: `backend/alembic/versions/c3d5e7f9a1b2_venta_multipedido.py`
- Modify: `backend/app/models/venta.py`, `backend/app/models/pedido.py`, `backend/app/schemas/venta.py`, `backend/app/services/pedido_service.py`, `backend/app/services/venta_service.py`, `backend/app/services/reporte_service.py`
- Test: `backend/tests/test_ventas_api.py` (+ payloads en el resto de `backend/tests/`)

**Interfaces:**
- Produces: `POST /api/v1/ventas` con body `{"ids_pedidos": [int, ...], "pagos": [...]}` → `VentaOut` con `ids_pedidos: list[int]` (ya no `id_pedido`). `tiene_pedido_activo(db, id_mesa, excepto_ids: list[int] | None = None)`. Las Tareas 2–4 (móvil) consumen este shape.

- [ ] **Paso 1: Tests RED — nuevos casos de cuenta en `test_ventas_api.py`**

Añadir al final del archivo (reutiliza los helpers existentes `_pedido`, `_otra_ronda`, `_metodo_id`, `_estado_mesa`):

```python
def _entregar(client, db, admin_headers, id_pedido):
    """Avanza un pedido Pendiente hasta Entregado por la API de transiciones."""
    from app.models import EstadoPedido

    for nombre in ("En preparación", "Listo", "Entregado"):
        est = (
            db.query(EstadoPedido)
            .filter(EstadoPedido.nombre_estado == nombre)
            .one()
        )
        r = client.patch(
            f"/api/v1/pedidos/{id_pedido}/estado",
            headers=admin_headers,
            json={"id_estado": est.id_estado},
        )
        assert r.status_code == 200


def test_cobrar_cuenta_de_dos_rondas_201(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=620, precio=116.0)
    ronda2 = _otra_ronda(client, db, admin_headers, pedido["id_mesa"], precio=58.0)
    _entregar(client, db, admin_headers, pedido["id_pedido"])
    _entregar(client, db, admin_headers, ronda2["id_pedido"])
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"], ronda2["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["total"]) == 174.0
    assert float(body["cambio"]) == 26.0
    assert sorted(body["ids_pedidos"]) == sorted(
        [pedido["id_pedido"], ronda2["id_pedido"]]
    )
    assert body["folio"].startswith("V-")
    assert _estado_mesa(client, admin_headers, pedido["id_mesa"]) == "Disponible"


def test_cobrar_cuenta_mesas_distintas_409(client, db, admin_headers, cajero_headers):
    p1 = _pedido(client, db, admin_headers, numero=621)
    p2 = _pedido(client, db, admin_headers, numero=622)
    _entregar(client, db, admin_headers, p1["id_pedido"])
    _entregar(client, db, admin_headers, p2["id_pedido"])
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [p1["id_pedido"], p2["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}],
        },
    )
    assert r.status_code == 409
    assert "misma mesa" in r.json()["detail"]


def test_cobrar_cuenta_con_ronda_sin_entregar_409(
    client, db, admin_headers, cajero_headers
):
    pedido = _pedido(client, db, admin_headers, numero=623)
    ronda2 = _otra_ronda(client, db, admin_headers, pedido["id_mesa"])
    _entregar(client, db, admin_headers, pedido["id_pedido"])  # ronda2 queda Pendiente
    efectivo = _metodo_id(db, "Efectivo")
    ids = [pedido["id_pedido"], ronda2["id_pedido"]]
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={"ids_pedidos": ids, "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}]},
    )
    assert r.status_code == 409
    assert "sin entregar" in r.json()["detail"]
    assert _estado_mesa(client, admin_headers, pedido["id_mesa"]) == "Ocupada"
    # Tras entregar la ronda pendiente, la misma cuenta sí se cobra.
    _entregar(client, db, admin_headers, ronda2["id_pedido"])
    r2 = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={"ids_pedidos": ids, "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}]},
    )
    assert r2.status_code == 201


def test_cobrar_cuenta_con_ronda_ya_cobrada_409(
    client, db, admin_headers, cajero_headers
):
    pedido = _pedido(client, db, admin_headers, numero=624, precio=116.0)
    ronda2 = _otra_ronda(client, db, admin_headers, pedido["id_mesa"])
    _entregar(client, db, admin_headers, pedido["id_pedido"])
    _entregar(client, db, admin_headers, ronda2["id_pedido"])
    efectivo = _metodo_id(db, "Efectivo")
    r1 = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 116.0}],
        },
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"], ronda2["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}],
        },
    )
    assert r2.status_code == 409
    assert "ya fue cobrado" in r2.json()["detail"]


def test_cobrar_ids_repetidos_422(client, db, admin_headers, cajero_headers):
    pedido = _pedido(client, db, admin_headers, numero=625)
    efectivo = _metodo_id(db, "Efectivo")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "ids_pedidos": [pedido["id_pedido"], pedido["id_pedido"]],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 500.0}],
        },
    )
    assert r.status_code == 422
```

- [ ] **Paso 2: Actualizar los payloads existentes de `POST /ventas` al shape nuevo**

Localizar todos los usos: `grep -rn '"id_pedido"' backend/tests/`. Solo cambian los que forman **el body de `POST /api/v1/ventas`** (los demás usos de `id_pedido` — crear pedidos, transiciones, asserts sobre pedidos — quedan igual):
- `json={"id_pedido": X, "pagos": ...}` → `json={"ids_pedidos": [X], "pagos": ...}` (incluye el helper `_cobrar_efectivo` de `test_ventas_api.py` y cualquier POST de ventas en `test_reportes_api.py` u otros).
- Asserts sobre la respuesta de venta `body["id_pedido"] == X` → `body["ids_pedidos"] == [X]`.

- [ ] **Paso 3: Correr `test_ventas_api.py` → los tests nuevos fallan** (422 de Pydantic por `ids_pedidos` desconocido / campo faltante).

- [ ] **Paso 4: Migración Alembic**

`backend/alembic/versions/c3d5e7f9a1b2_venta_multipedido.py`:

```python
"""venta multi-pedido: la FK se invierte a pedidos.id_venta

Revision ID: c3d5e7f9a1b2
Revises: 7f3a9c2b1d84
Create Date: 2026-08-11
"""
import sqlalchemy as sa
from alembic import op

revision = "c3d5e7f9a1b2"
down_revision = "7f3a9c2b1d84"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pedidos", sa.Column("id_venta", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "pedidos_id_venta_fkey", "pedidos", "ventas", ["id_venta"], ["id_venta"]
    )
    op.create_index("ix_pedidos_id_venta", "pedidos", ["id_venta"])
    # Backfill: cada venta existente (1:1) marca a su pedido.
    op.execute(
        "UPDATE pedidos SET id_venta = v.id_venta "
        "FROM ventas v WHERE v.id_pedido = pedidos.id_pedido"
    )
    # Postgres elimina en cascada el unique y la FK que cuelgan de la columna.
    op.drop_column("ventas", "id_pedido")


def downgrade() -> None:
    # Parcial: una venta multi-pedido conserva solo su primera ronda (mismo
    # criterio de irreversibilidad aceptado en 7f3a9c2b1d84).
    op.add_column("ventas", sa.Column("id_pedido", sa.Integer(), nullable=True))
    op.execute(
        "UPDATE ventas SET id_pedido = ("
        "SELECT MIN(p.id_pedido) FROM pedidos p WHERE p.id_venta = ventas.id_venta)"
    )
    op.alter_column("ventas", "id_pedido", nullable=False)
    op.create_foreign_key(
        "ventas_id_pedido_fkey", "ventas", "pedidos", ["id_pedido"], ["id_pedido"]
    )
    op.create_unique_constraint("ventas_id_pedido_key", "ventas", ["id_pedido"])
    op.drop_index("ix_pedidos_id_venta", table_name="pedidos")
    op.drop_column("pedidos", "id_venta")
```

- [ ] **Paso 5: Modelos**

En `backend/app/models/venta.py`, clase `Venta`: eliminar el bloque `id_pedido = Column(...)`, actualizar el docstring a `"""Registro financiero del cobro de una cuenta (uno o más pedidos de la misma mesa)."""` y añadir junto a las relaciones:

```python
    pedidos = relationship(
        "Pedido",
        back_populates="venta",
        lazy="selectin",
        order_by="Pedido.id_pedido",
    )
```

En `backend/app/models/pedido.py`, clase `Pedido`: después de `id_estado` añadir la columna, y junto a las relaciones la inversa:

```python
    id_venta = Column(
        Integer, ForeignKey("ventas.id_venta"), nullable=True, index=True
    )
```

```python
    venta = relationship("Venta", back_populates="pedidos")
```

- [ ] **Paso 6: `pedido_service.py` — pedido activo por `id_venta` y exclusión por lista**

En `condiciones_pedido_activo` la condición de "no cobrado" deja la subconsulta:

```python
    return (
        Pedido.id_estado != cancelado,
        Pedido.id_venta.is_(None),
    )
```

(quitar el import de `Venta` si queda sin uso). `tiene_pedido_activo` generaliza la exclusión:

```python
def tiene_pedido_activo(
    db: Session, id_mesa: int, excepto_ids: list[int] | None = None
) -> bool:
    """True si la mesa tiene al menos un pedido activo (ni cancelado ni cobrado).

    `excepto_ids` excluye los pedidos que se están cerrando (cobro o
    cancelación): la consulta no debe depender de si su venta o su cambio de
    estado ya se reflejaron en la sesión.
    """
    condiciones = [Pedido.id_mesa == id_mesa, *condiciones_pedido_activo(db)]
    if excepto_ids:
        condiciones.append(Pedido.id_pedido.not_in(excepto_ids))
    stmt = select(Pedido.id_pedido).where(*condiciones)
    return db.execute(stmt).first() is not None
```

En `cancelar`, la llamada pasa a `excepto_ids=[pedido.id_pedido]`.

- [ ] **Paso 7: Schemas**

En `backend/app/schemas/venta.py`:

```python
class VentaCreate(BaseModel):
    ids_pedidos: list[int] = Field(min_length=1)
    pagos: list[PagoIn] = Field(min_length=1)
```

y en `VentaOut` reemplazar `id_pedido: int` por `ids_pedidos: list[int]`.

- [ ] **Paso 8: `venta_service.py` — cobrar N pedidos**

Reescribir `cobrar` y ajustar `to_out`:

```python
def cobrar(db: Session, data: VentaCreate, usuario) -> Venta:
    if usuario.rol.nombre_rol not in _ROLES_COBRO:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rol no autorizado para cobrar")

    ids = data.ids_pedidos
    if len(set(ids)) != len(ids):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Pedidos repetidos en el cobro"
        )

    pedidos: list[Pedido] = []
    for id_pedido in ids:
        pedido = db.get(Pedido, id_pedido)
        if pedido is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
        pedidos.append(pedido)

    for pedido in pedidos:
        if pedido.estado.nombre_estado == "Cancelado":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "No se puede cobrar un pedido cancelado"
            )
        if pedido.id_venta is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "El pedido ya fue cobrado")

    if len({p.id_mesa for p in pedidos}) > 1:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Los pedidos del cobro deben ser de la misma mesa"
        )
    # La cuenta completa (más de una ronda) exige todo Entregado; la ronda
    # suelta conserva la regla histórica (cobrable en cualquier estado no
    # cancelado) para no romper el flujo existente.
    if len(pedidos) > 1 and any(
        p.estado.nombre_estado != "Entregado" for p in pedidos
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La mesa tiene una ronda sin entregar"
        )

    for p in data.pagos:
        if db.get(MetodoPago, p.id_metodo_pago) is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Método de pago {p.id_metodo_pago} inexistente",
            )

    total = sum((p.total for p in pedidos), Decimal("0"))
    suma = sum((p.monto for p in data.pagos), Decimal("0"))
    if suma < total:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Pago insuficiente")

    venta = Venta(id_usuario=usuario.id_usuario, total=total)
    db.add(venta)
    db.flush()
    for pedido in pedidos:
        pedido.id_venta = venta.id_venta
    for p in data.pagos:
        db.add(
            Pago(
                id_venta=venta.id_venta,
                id_metodo_pago=p.id_metodo_pago,
                monto=p.monto,
                referencia=p.referencia,
            )
        )
    db.add(Ticket(id_venta=venta.id_venta, folio=f"V-{venta.id_venta:06d}"))
    # La mesa se libera solo si fuera de esta cuenta no queda ronda activa
    # (el id_venta recién asignado puede no estar flusheado: exclusión explícita).
    if not pedido_service.tiene_pedido_activo(
        db, pedidos[0].id_mesa, excepto_ids=[p.id_pedido for p in pedidos]
    ):
        pedidos[0].mesa.estado = "Disponible"
    db.commit()
    db.refresh(venta)
    return venta
```

En `to_out`, reemplazar `id_pedido=venta.id_pedido` por:

```python
        ids_pedidos=[p.id_pedido for p in venta.pedidos],
```

- [ ] **Paso 9: `reporte_service.py` — joins por la FK nueva**

- Línea ~131 (`top_productos`): `.join(Pedido, Pedido.id_pedido == Venta.id_pedido)` → `.join(Pedido, Pedido.id_venta == Venta.id_venta)`.
- En `detalle_ventas`, el filtro de mesero deja el join (duplicaría filas con N rondas) y usa la relación:

```python
    if id_usuario is not None:
        # id_usuario = mesero que tomó alguna ronda de la cuenta, no el cajero.
        query = query.filter(Venta.pedidos.any(Pedido.id_usuario == id_usuario))
```

- Más abajo, `pedido = db.get(Pedido, v.id_pedido)` → `pedido = v.pedidos[0] if v.pedidos else None` (todas las rondas son de la misma mesa).

- [ ] **Paso 10: Suite backend completa en verde** (contenedor efímero del bloque "Cómo correr los tests"). Esperado: 239 existentes adaptados + 5 nuevos ≈ **244**. Los tests del PR #31 (liberación con dos rondas cobradas por separado) deben pasar **sin tocar su lógica** (solo el payload del Paso 2).

- [ ] **Paso 11: Commit**

```bash
git add backend/
git commit -m "feat(api): una venta cobra la cuenta completa de la mesa (N pedidos, un folio)"
```

## Tarea 2 — Móvil: cliente API y helpers puros de cuenta

**Files:**
- Modify: `mobile/src/api/client.ts`, `mobile/src/api/client.test.ts`, `mobile/src/lib/caja.ts`
- Test: `mobile/src/lib/caja.test.ts`

**Interfaces:**
- Consumes: `POST /ventas {ids_pedidos, pagos}` de la Tarea 1.
- Produces: `cobrarVenta(access, ids_pedidos: number[], pagos): Promise<Venta>`; `Venta.ids_pedidos: number[]`; `agruparPorMesa(pedidos: Pedido[]): CuentaMesa[]`; `cuentaCobrable(pedidos): boolean`; tipo `CuentaMesa = { id_mesa, numero_mesa, pedidos, total, cobrable }`. Las Tareas 3–4 consumen exactamente estos nombres.

- [ ] **Paso 1: Tests RED en `mobile/src/lib/caja.test.ts`**

Añadir al final (los totales son **Decimal-strings**, como manda la API):

```ts
import { agruparPorMesa, cuentaCobrable } from "./caja";
import type { Pedido } from "@/api/client";

const ped = (id: number, mesa: number, total: string, estado = "Entregado") =>
  ({
    id_pedido: id,
    id_mesa: mesa,
    mesa: { numero_mesa: mesa },
    estado: { id_estado: 0, nombre_estado: estado },
    total,
    detalle: [],
  }) as unknown as Pedido;

test("agruparPorMesa: agrupa, suma en centavos y ordena por mesa", () => {
  const cuentas = agruparPorMesa([
    ped(11, 4, "58.00"),
    ped(10, 2, "0.10"),
    ped(12, 4, "116.00"),
    ped(13, 2, "0.20"),
  ]);
  expect(cuentas.map((c) => c.numero_mesa)).toEqual([2, 4]);
  expect(cuentas[0].total).toBe(0.3); // 0.10 + 0.20 exacto, sin residuo de floats
  expect(cuentas[1].total).toBe(174);
  expect(cuentas[1].pedidos.map((p) => p.id_pedido)).toEqual([11, 12]); // rondas por id
});

test("cuentaCobrable: solo con todas las rondas Entregadas", () => {
  expect(cuentaCobrable([ped(1, 1, "10.00"), ped(2, 1, "10.00")])).toBe(true);
  expect(cuentaCobrable([ped(1, 1, "10.00"), ped(2, 1, "10.00", "Pendiente")])).toBe(false);
  expect(cuentaCobrable([])).toBe(false);
});

test("agruparPorMesa: la cuenta con ronda en cocina queda no cobrable", () => {
  const [c] = agruparPorMesa([ped(1, 7, "10.00"), ped(2, 7, "10.00", "Listo")]);
  expect(c.cobrable).toBe(false);
});
```

- [ ] **Paso 2: Correr `npx jest src/lib/caja.test.ts` → fallan** (exports inexistentes).

- [ ] **Paso 3: Implementación en `mobile/src/lib/caja.ts`**

Al inicio del archivo:

```ts
import type { Pedido } from "@/api/client";
```

Al final:

```ts
export type CuentaMesa = {
  id_mesa: number;
  numero_mesa: number;
  pedidos: Pedido[]; // rondas ordenadas por id_pedido
  total: number; // suma acumulada en centavos
  cobrable: boolean; // todas las rondas Entregadas
};

export function cuentaCobrable(pedidos: Pick<Pedido, "estado">[]): boolean {
  return (
    pedidos.length > 0 &&
    pedidos.every((p) => p.estado.nombre_estado === "Entregado")
  );
}

export function agruparPorMesa(pedidos: Pedido[]): CuentaMesa[] {
  const porMesa = new Map<number, Pedido[]>();
  for (const p of pedidos) {
    const lista = porMesa.get(p.id_mesa) ?? [];
    lista.push(p);
    porMesa.set(p.id_mesa, lista);
  }
  return Array.from(porMesa.values())
    .map((lista) => {
      const rondas = [...lista].sort((a, b) => a.id_pedido - b.id_pedido);
      const totalCent = rondas.reduce(
        (s, p) => s + Math.round(Number(p.total) * 100),
        0
      );
      return {
        id_mesa: rondas[0].id_mesa,
        numero_mesa: rondas[0].mesa.numero_mesa,
        pedidos: rondas,
        total: totalCent / 100,
        cobrable: cuentaCobrable(rondas),
      };
    })
    .sort((a, b) => a.numero_mesa - b.numero_mesa);
}
```

- [ ] **Paso 4: `mobile/src/api/client.ts` — shape nuevo de venta**

En `type Venta`: reemplazar `id_pedido: number;` por `ids_pedidos: number[];`. Reemplazar `cobrarVenta`:

```ts
export async function cobrarVenta(
  access: string,
  ids_pedidos: number[],
  pagos: { id_metodo_pago: number; monto: number; referencia?: string }[]
): Promise<Venta> {
  const { data } = await http.post(
    "/ventas",
    { ids_pedidos, pagos },
    authCfg(access)
  );
  return data;
}
```

- [ ] **Paso 5: Actualizar `mobile/src/api/client.test.ts`**

`grep -n "cobrarVenta\|id_pedido" mobile/src/api/client.test.ts`: en los tests de `cobrarVenta`, la llamada pasa de `cobrarVenta(tok, 5, pagos)` a `cobrarVenta(tok, [5], pagos)` y el assert del body esperado de `{ id_pedido: 5, ... }` a `{ ids_pedidos: [5], ... }`. Si algún stub de respuesta de venta trae `id_pedido`, cambia a `ids_pedidos: [5]`.

- [ ] **Paso 6: `npx jest src/lib/caja.test.ts src/api/client.test.ts` en verde.** `npx tsc --noEmit` va a fallar por `cobro.tsx` (aún llama `cobrarVenta(access, pid, ...)`) — se arregla en la Tarea 4; no lo "parches" aquí.

- [ ] **Paso 7: Commit**

```bash
git add mobile/src/lib/caja.ts mobile/src/lib/caja.test.ts mobile/src/api/client.ts mobile/src/api/client.test.ts
git commit -m "feat(mobile): agrupador de cuentas por mesa y cliente de venta multi-pedido"
```

## Tarea 3 — Móvil: Caja agrupada por mesa

**Files:**
- Modify: `mobile/src/app/caja/index.tsx`

**Interfaces:**
- Consumes: `agruparPorMesa`, `CuentaMesa` (Tarea 2).
- Produces: navegación `router.push('/caja/cobro?ids=1,2,3')` — la Tarea 4 lee el param `ids` (CSV).

- [ ] **Paso 1: Reescribir la lista como tarjetas de cuenta**

Imports nuevos: `import { agruparPorMesa, CuentaMesa } from "@/lib/caja";` y `Badge` desde `@/ui` (`import { Badge, BottomNav } from "@/ui";`). Estado nuevo dentro del componente:

```tsx
  const [expandidas, setExpandidas] = useState<Set<number>>(new Set());
```

El subtítulo del header pasa a `Cuentas por mesa`. El `FlatList` se reemplaza por:

```tsx
        <FlatList
          data={agruparPorMesa(pedidos)}
          keyExtractor={(c) => String(c.id_mesa)}
          contentContainerStyle={styles.list}
          renderItem={({ item }) => (
            <CuentaCard
              cuenta={item}
              expandida={expandidas.has(item.id_mesa)}
              onToggle={() =>
                setExpandidas((s) => {
                  const n = new Set(s);
                  n.has(item.id_mesa) ? n.delete(item.id_mesa) : n.add(item.id_mesa);
                  return n;
                })
              }
            />
          )}
        />
```

Componente nuevo en el mismo archivo (arriba de `Caja`):

```tsx
function CuentaCard({
  cuenta,
  expandida,
  onToggle,
}: {
  cuenta: CuentaMesa;
  expandida: boolean;
  onToggle: () => void;
}) {
  const varias = cuenta.pedidos.length > 1;
  const ids = cuenta.pedidos.map((p) => p.id_pedido).join(",");
  return (
    <View style={styles.card}>
      <View style={styles.cardHead}>
        <View>
          <Text style={styles.mesa}>Mesa {cuenta.numero_mesa}</Text>
          <Text style={styles.meta}>
            {varias
              ? `${cuenta.pedidos.length} rondas`
              : `#${cuenta.pedidos[0].id_pedido}`}
          </Text>
        </View>
        <Text style={styles.total}>{money(cuenta.total)}</Text>
      </View>
      {!cuenta.cobrable && (
        <Badge label="ronda en cocina" variant="warn" style={styles.badge} />
      )}
      <TouchableOpacity
        style={[styles.cobrarBtn, !cuenta.cobrable && styles.cobrarBtnOff]}
        disabled={!cuenta.cobrable}
        onPress={() => router.push(`/caja/cobro?ids=${ids}` as any)}
      >
        <Text style={styles.cobrarTxt}>
          {varias ? "Cobrar cuenta" : "Cobrar"}
        </Text>
      </TouchableOpacity>
      {varias && (
        <TouchableOpacity onPress={onToggle}>
          <Text style={styles.verRondas}>
            {expandida ? "Ocultar rondas" : "Ver rondas"}
          </Text>
        </TouchableOpacity>
      )}
      {expandida &&
        cuenta.pedidos.map((p) => (
          <TouchableOpacity
            key={p.id_pedido}
            style={styles.ronda}
            onPress={() => router.push(`/caja/cobro?ids=${p.id_pedido}` as any)}
          >
            <Text style={styles.rondaTxt}>
              #{p.id_pedido} · {p.estado.nombre_estado}
            </Text>
            <Text style={styles.rondaTotal}>{money(p.total)}</Text>
          </TouchableOpacity>
        ))}
    </View>
  );
}
```

Estilos: el `card` existente pierde `flexDirection/justifyContent/alignItems` (los hereda `cardHead`) y se añaden:

```ts
  cardHead: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  badge: { alignSelf: "flex-start", marginTop: spacing.sm },
  cobrarBtn: {
    marginTop: spacing.md,
    height: 40,
    borderRadius: radius.button,
    backgroundColor: colors.accent,
    alignItems: "center",
    justifyContent: "center",
  },
  cobrarBtnOff: { backgroundColor: colors.disabled },
  cobrarTxt: { color: colors.onAccent, fontFamily: fonts.bold, fontSize: 14 },
  verRondas: {
    color: colors.accent,
    fontFamily: fonts.semibold,
    fontSize: 13,
    paddingTop: spacing.sm,
    textAlign: "center",
  },
  ronda: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderTopWidth: 1,
    borderTopColor: colors.border,
  },
  rondaTxt: { fontFamily: fonts.body, fontSize: 13, color: colors.coffee700 },
  rondaTotal: { fontFamily: fonts.semibold, fontSize: 13, color: colors.coffee900 },
```

(`radius.button` ya existe en el theme — lo usa `cobro.tsx`.)

- [ ] **Paso 2: `npm test` en verde** (no hay tests de componentes; la suite protege las libs). `tsc` aún falla solo por `cobro.tsx` (Tarea 4).

- [ ] **Paso 3: Commit**

```bash
git add mobile/src/app/caja/index.tsx
git commit -m "feat(mobile): Caja agrupa las rondas en cuentas por mesa"
```

## Tarea 4 — Móvil: cobro de la cuenta completa y ticket

**Files:**
- Modify: `mobile/src/app/caja/cobro.tsx`, `mobile/src/lib/ticket.ts`
- Test: `mobile/src/lib/ticket.test.ts`

**Interfaces:**
- Consumes: param `ids` CSV (Tarea 3), `cobrarVenta(access, ids, pagos)` (Tarea 2).
- Produces: `ticketHtml(venta: Venta, pedidos: Pedido[]): string` (antes recibía `Pedido | null`).

- [ ] **Paso 1: Tests RED de `ticket.test.ts`**

`grep -n "ticketHtml" mobile/src/lib/ticket.test.ts`: las llamadas pasan de `ticketHtml(venta, pedido)` a `ticketHtml(venta, [pedido])` (y `ticketHtml(venta, null)` → `ticketHtml(venta, [])`). Añadir un test de cuenta con dos rondas:

```ts
test("ticketHtml: cuenta de dos rondas lista las líneas de ambas", () => {
  const linea = (nombre: string) => ({
    producto: { nombre_producto: nombre },
    cantidad: 1,
    precio_unitario: "58.00",
    subtotal: "58.00",
  });
  const p1 = { mesa: { numero_mesa: 4 }, detalle: [linea("Latte")] } as any;
  const p2 = { mesa: { numero_mesa: 4 }, detalle: [linea("Croissant")] } as any;
  const html = ticketHtml(ventaBase, [p1, p2]);
  expect(html).toContain("Latte");
  expect(html).toContain("Croissant");
});
```

(usar el stub de venta ya existente en el archivo como `ventaBase`; si tiene otro nombre, reutilizarlo tal cual).

- [ ] **Paso 2: Correr `npx jest src/lib/ticket.test.ts` → falla por la firma.**

- [ ] **Paso 3: `ticket.ts` — firma de lista**

```ts
export function ticketHtml(venta: Venta, pedidos: Pedido[]): string {
```

Dentro: `const mesa = pedidos[0]?.mesa.numero_mesa;` y las líneas salen de todas las rondas:

```ts
  const lineas = pedidos
    .flatMap((p) => p.detalle)
    .map(
      (d) => `
      <tr>
        <td>${esc(d.producto.nombre_producto)}<br>
          <span class="mut">${d.cantidad} × ${money(d.precio_unitario)}</span></td>
        <td class="num">${money(d.subtotal)}</td>
      </tr>`
    )
    .join("");
```

(el template del `<tr>` es el mismo de hoy, solo cambia la fuente de las líneas; donde el HTML imprimía la mesa a partir de `pedido?.mesa`, usar la constante `mesa`). Actualizar el docstring: «los pedidos aportan mesa y líneas; con lista vacía el ticket sale solo con los totales de la venta».

- [ ] **Paso 4: `cobro.tsx` — cargar y cobrar N pedidos**

Cambios puntuales (el resto de la pantalla — líneas de pago, división, validaciones — no se toca):

1. Params y estado:
```tsx
  const { ids } = useLocalSearchParams<{ ids: string }>();
  const idsPedidos = (ids ?? "")
    .split(",")
    .map(Number)
    .filter((n) => Number.isFinite(n) && n > 0);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
```
(fuera `id_pedido`/`pid`/`pedido`; donde el JSX usaba `pedido`, usar `pedidos[0]` para mesa y las variables de abajo para líneas).

2. Carga (en el `useEffect`, misma estructura `try/catch`):
```tsx
        const [ps, ms] = await Promise.all([
          Promise.all(idsPedidos.map((i) => getPedido(access, i))),
          getMetodosPago(access),
        ]);
        setPedidos(ps);
        setMetodos(ms);
```
(dependencias del efecto: `[access, ids]`).

3. Total y detalle-unión con etiqueta de ronda:
```tsx
  const total =
    pedidos.reduce((s, p) => s + Math.round(Number(p.total) * 100), 0) / 100;
  const varias = pedidos.length > 1;
  type LineaRonda = Pedido["detalle"][number] & { ronda: number };
  const detalle: LineaRonda[] = pedidos.flatMap((p, r) =>
    p.detalle.map((d) => ({ ...d, ronda: r + 1 }))
  );
```
(la constante `detalle` reemplaza a `pedido?.detalle ?? []`; `crearAsignacion`, `unidadesRestantes`, `totalPersona` y el resto de `lib/split.ts` la consumen igual — es un arreglo de líneas).

4. Título y listado superior: `Cobro — Mesa {pedidos[0]?.mesa.numero_mesa}` + (si `varias`) sufijo ` · ${pedidos.length} rondas`; las líneas del resumen superior y el `divMeta` de la división añaden la etiqueta cuando `varias`:
```tsx
        {detalle.map((d, i) => (
          <Text key={i} style={styles.linea}>
            {d.cantidad} × {d.producto.nombre_producto}
            {varias ? `  · R${d.ronda}` : ""}
          </Text>
        ))}
```
(en `divMeta`: `{money(d.precio_unitario)} c/u{varias ? ` · R${d.ronda}` : ""}...`).

5. Confirmar y comprobante: `cobrarVenta(access, idsPedidos, aPayload(parseadas))`; en el comprobante, `Mesa` sale de `pedidos[0]` y las líneas de `pedidos.flatMap((p) => p.detalle)`; `imprimir` llama `ticketHtml(v, pedidos)`.

- [ ] **Paso 5: `npm test` completo + `npx tsc --noEmit` limpios** (aquí ya no queda ninguna referencia al shape viejo).

- [ ] **Paso 6: Commit**

```bash
git add mobile/src/app/caja/cobro.tsx mobile/src/lib/ticket.ts mobile/src/lib/ticket.test.ts
git commit -m "feat(mobile): cobro de la cuenta completa con division y ticket multi-ronda"
```

## Tarea 5 — Verificación final, docs y PR

- [ ] Suite backend completa en contenedor efímero (≈244) + `npm test` (≈112: 109 + ~3) + `tsc` limpios.
- [ ] **Ejercitar la migración desde cero:** detener el stack principal (`docker compose stop`, lo corre el usuario si el permiso lo bloquea) y levantar el del worktree (`docker compose up -d` en el worktree → proyecto propio con BD vacía) + `alembic upgrade head` + `python -m app.db.seed` + `python -m app.db.seed_demo`. Verificar `alembic downgrade -1` + `upgrade head` sin error.
- [ ] **Smoke en dispositivo (manual, con el usuario):** dos rondas en la misma mesa → Caja muestra una cuenta «2 rondas» (badge «ronda en cocina» mientras no estén Entregadas, botón deshabilitado) → entregar ambas → cobrar la cuenta con división entre 2 personas → **un folio**, ticket con todas las líneas, mesa liberada. Además: cobrar una ronda suelta desde «Ver rondas» y verificar que la otra sigue cobrable. (Metro: receta del portproxy si el túnel falla — memoria `expo-tunnel-ngrok-portproxy`.)
- [ ] Actualizar `progress.md` en la rama (sección nueva + conteos de tests; nota de despliegue: el ritual post-merge corre `alembic upgrade head` sobre la BD real — verificar backfill con `SELECT COUNT(*) FROM ventas v WHERE NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.id_venta = v.id_venta)` → 0).
- [ ] Push + PR hacia `main`.
