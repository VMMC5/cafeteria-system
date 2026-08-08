# Guard de mesa Ocupada en la API — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La API deja de permitir que se cambie el estado de una mesa que tiene un pedido activo, y deja de aceptar `"Ocupada"` como estado asignado a mano — cerrando el hueco que hoy solo cubre el panel web.

**Architecture:** La regla "un pedido activo es el que no está cancelado ni cobrado" ya existe implícita dentro de `venta_service.listar_por_cobrar`. Se extrae a `pedido_service` como predicado único y se consume desde dos lugares: el listado de pedidos por cobrar (sin cambio de comportamiento) y el nuevo guard en `mesa_service.update`. El guard se apoya en el pedido real, no en la bandera `mesa.estado`, para que una mesa marcada Ocupada por error se pueda destrabar.

**Tech Stack:** FastAPI + SQLAlchemy + pytest.

**Spec:** `docs/superpowers/specs/2026-08-08-guard-ocupada-api-design.md`

## Global Constraints

- **Solo `backend/`.** El panel web no se toca en este slice; el hardening CSRF es un slice aparte.
- **La ruta es `PATCH /api/v1/mesas/{id_mesa}`** (no PUT). El cuerpo es `MesaUpdate`, con todos los campos opcionales.
- **Códigos exactos:** destino `"Ocupada"` → **422**; mesa con pedido activo → **409**. Cualquier otro cambio de estado → 200.
- **El guard solo mira `estado`.** `numero_mesa`, `capacidad` y `ubicacion` siguen editables aunque la mesa tenga un pedido activo.
- **El guard solo se dispara si el estado cambia de verdad** (`data.estado is not None and data.estado != obj.estado`), para que reenviar el mismo valor no falle.
- **Sin ciclos de import:** `pedido_service` NO debe importar `venta_service` ni `mesa_service`. Los que importan a `pedido_service` son `venta_service` y `mesa_service`.
- **Commits en español**, formato `tipo(scope): descripción`.
- **Rama:** `feat/api-guard-ocupada` (worktree aislado bajo `.claude/worktrees/`).
- **Tests del backend en worktree:** los contenedores en marcha montan el checkout principal, así que `docker compose exec api pytest` probaría el código equivocado. Usar un contenedor efímero que monte el worktree:
  ```bash
  docker run --rm --network cafeteria-system_default --user $(id -u):$(id -g) \
    --env-file <worktree>/.env -v <worktree>/backend:/code -w /code \
    cafeteria-system-api pytest -q
  ```
  Copiar antes el `.env` del checkout principal al worktree (está gitignorado). El `--user` evita que pytest deje `__pycache__` como root y bloquee luego el borrado del worktree.
- **Baseline:** 206 tests del backend en verde antes de empezar.

## Estructura de archivos

| Archivo | Responsabilidad | Acción |
|---|---|---|
| `backend/app/services/pedido_service.py` | `condiciones_pedido_activo` + `tiene_pedido_activo` | Modificar |
| `backend/app/services/venta_service.py` | `listar_por_cobrar` consume el predicado compartido | Modificar |
| `backend/tests/test_pedido_service.py` | Tests del predicado | Crear |
| `backend/app/services/mesa_service.py` | El guard en `update` | Modificar |
| `backend/tests/test_mesas_api.py` | Tests del guard vía API | Modificar |
| `progress.md` | Bitácora | Modificar |

**Orden:** Task 1 (predicado) → Task 2 (guard) → Task 3 (verificación + docs). Task 2 consume lo que produce Task 1.

---

### Task 1: Predicado único de "pedido activo"

**Files:**
- Modify: `backend/app/services/pedido_service.py`
- Modify: `backend/app/services/venta_service.py`
- Test: `backend/tests/test_pedido_service.py` (crear)

**Interfaces:**
- Consumes: nada (primera task).
- Produces (lo usa Task 2):
  - `pedido_service.condiciones_pedido_activo(db: Session) -> tuple` — condiciones SQLAlchemy `(Pedido.id_estado != <id de Cancelado>, Pedido.id_pedido.not_in(select(Venta.id_pedido)))`.
  - `pedido_service.tiene_pedido_activo(db: Session, id_mesa: int) -> bool`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `backend/tests/test_pedido_service.py`. Los fixtures `client`, `db`, `admin_headers` y `cajero_headers` vienen de `conftest.py`:

```python
from app.services import pedido_service


def _mesa(client, admin_headers, numero):
    return client.post(
        "/api/v1/mesas",
        headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()


def _pedido_en_mesa(client, db, admin_headers, numero):
    from app.models import Categoria

    mesa = _mesa(client, admin_headers, numero)
    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": f"Item{numero}",
            "precio_venta": 116.0,
            "disponible": True,
        },
    ).json()
    pedido = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()
    return mesa, pedido


def test_tiene_pedido_activo_con_pedido_abierto(client, db, admin_headers):
    mesa, _ = _pedido_en_mesa(client, db, admin_headers, 801)
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is True


def test_tiene_pedido_activo_falso_sin_pedidos(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, 802)
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is False


def test_tiene_pedido_activo_falso_tras_cobrar(client, db, admin_headers, cajero_headers):
    from app.models import MetodoPago

    mesa, pedido = _pedido_en_mesa(client, db, admin_headers, 803)
    efectivo = (
        db.query(MetodoPago)
        .filter(MetodoPago.nombre_metodo == "Efectivo")
        .one()
        .id_metodo_pago
    )
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
        },
    )
    assert r.status_code == 201
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is False


def test_tiene_pedido_activo_falso_tras_cancelar(client, db, admin_headers):
    mesa, pedido = _pedido_en_mesa(client, db, admin_headers, 804)
    r = client.post(
        f"/api/v1/pedidos/{pedido['id_pedido']}/cancelar",
        headers=admin_headers,
        json={"motivo": "prueba"},
    )
    assert r.status_code == 200
    assert pedido_service.tiene_pedido_activo(db, mesa["id_mesa"]) is False
```

El archivo son los dos helpers seguidos de los **cuatro** tests, en ese orden: `con_pedido_abierto`, `falso_sin_pedidos`, `falso_tras_cobrar`, `falso_tras_cancelar`. Los dos bloques de código de arriba son el archivo completo, en secuencia.

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `docker run --rm --network cafeteria-system_default --user $(id -u):$(id -g) --env-file <worktree>/.env -v <worktree>/backend:/code -w /code cafeteria-system-api pytest tests/test_pedido_service.py -v`
Expected: FAIL — `AttributeError: module 'app.services.pedido_service' has no attribute 'tiene_pedido_activo'`.

- [ ] **Step 3: Añadir el predicado y el helper en `pedido_service`**

En `backend/app/services/pedido_service.py`, añadir `Venta` al import de modelos. Hoy es una sola línea (`from app.models import Cancelacion, DetallePedido, EstadoPedido, Mesa, Pedido, Producto`); con `Venta` supera los 88 caracteres, así que queda en varias líneas:

```python
from app.models import (
    Cancelacion,
    DetallePedido,
    EstadoPedido,
    Mesa,
    Pedido,
    Producto,
    Venta,
)
```

Y añadir estas dos funciones al final del archivo:

```python
def condiciones_pedido_activo(db: Session) -> tuple:
    """Condiciones que definen un pedido **activo**: ni cancelado ni cobrado.

    Única definición de la regla. La comparten `venta_service.listar_por_cobrar`
    y el guard de estado de mesas: si divergieran, la API podría liberar una mesa
    que en realidad sigue ocupada.
    """
    cancelado = db.execute(
        select(EstadoPedido.id_estado).where(
            EstadoPedido.nombre_estado == "Cancelado"
        )
    ).scalar_one()
    return (
        Pedido.id_estado != cancelado,
        Pedido.id_pedido.not_in(select(Venta.id_pedido)),
    )


def tiene_pedido_activo(db: Session, id_mesa: int) -> bool:
    """True si la mesa tiene al menos un pedido activo (ni cancelado ni cobrado)."""
    stmt = select(Pedido.id_pedido).where(
        Pedido.id_mesa == id_mesa, *condiciones_pedido_activo(db)
    )
    return db.execute(stmt).first() is not None
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `docker run --rm --network cafeteria-system_default --user $(id -u):$(id -g) --env-file <worktree>/.env -v <worktree>/backend:/code -w /code cafeteria-system-api pytest tests/test_pedido_service.py -v`
Expected: PASS — 4 tests.

- [ ] **Step 5: Hacer que `listar_por_cobrar` consuma el predicado**

En `backend/app/services/venta_service.py`, añadir el import del servicio junto a los otros imports de `app.`:

```python
from app.services import pedido_service
```

Reemplazar el cuerpo de `listar_por_cobrar` por:

```python
def listar_por_cobrar(db: Session) -> list[Pedido]:
    stmt = (
        select(Pedido)
        .where(*pedido_service.condiciones_pedido_activo(db))
        .order_by(Pedido.id_pedido.desc())
    )
    return list(db.execute(stmt).scalars())
```

`EstadoPedido` queda sin uso en `venta_service` tras este cambio: **quitarlo de la lista de imports de modelos**. Verificar con `grep -n 'EstadoPedido' backend/app/services/venta_service.py` que no queda ninguna referencia.

- [ ] **Step 6: Verificar que no hubo regresión en el listado por cobrar**

Run: `docker run --rm --network cafeteria-system_default --user $(id -u):$(id -g) --env-file <worktree>/.env -v <worktree>/backend:/code -w /code cafeteria-system-api pytest tests/test_ventas_api.py tests/test_venta_service.py tests/test_pedido_service.py -v`
Expected: PASS — los tests de ventas siguen verdes (el comportamiento y el orden `id_pedido` descendente no cambian) más los 4 nuevos.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/pedido_service.py backend/app/services/venta_service.py backend/tests/test_pedido_service.py
git commit -m "refactor(api): extraer el predicado de pedido activo a pedido_service"
```

---

### Task 2: El guard en `mesa_service.update`

**Files:**
- Modify: `backend/app/services/mesa_service.py`
- Test: `backend/tests/test_mesas_api.py`

**Interfaces:**
- Consumes: `pedido_service.tiene_pedido_activo(db, id_mesa) -> bool` (Task 1).
- Produces: el contrato de `PATCH /api/v1/mesas/{id_mesa}` descrito en las Global Constraints.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir al final de `backend/tests/test_mesas_api.py`. El helper `_nueva` ya existe arriba en ese archivo; estos helpers son nuevos:

```python
def _mesa_con_pedido(client, db, admin_headers, numero):
    """Crea una mesa y le abre un pedido: la mesa queda Ocupada de verdad."""
    from app.models import Categoria

    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=numero)
    ).json()
    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": f"Prod{numero}",
            "precio_venta": 116.0,
            "disponible": True,
        },
    ).json()
    pedido = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()
    return mesa, pedido


def test_cambiar_estado_con_pedido_activo_409(client, db, admin_headers):
    mesa, _ = _mesa_con_pedido(client, db, admin_headers, 901)
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Disponible"},
    )
    assert r.status_code == 409


def test_marcar_ocupada_a_mano_422(client, admin_headers):
    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=902)
    ).json()
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Ocupada"},
    )
    assert r.status_code == 422


def test_disponible_a_reservada_ok(client, admin_headers):
    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=903)
    ).json()
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Reservada"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "Reservada"


def test_destrabar_mesa_ocupada_sin_pedido_activo(client, db, admin_headers):
    """Una mesa marcada Ocupada sin pedido activo (dato viejo) SÍ se puede corregir."""
    from app.models import Mesa

    mesa = client.post(
        "/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=904)
    ).json()
    obj = db.get(Mesa, mesa["id_mesa"])
    obj.estado = "Ocupada"
    db.flush()

    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Disponible"},
    )
    assert r.status_code == 200
    assert r.json()["estado"] == "Disponible"


def test_reenviar_el_mismo_estado_no_falla(client, db, admin_headers):
    mesa, _ = _mesa_con_pedido(client, db, admin_headers, 905)
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Ocupada"},
    )
    assert r.status_code == 200


def test_editar_capacidad_con_pedido_activo_ok(client, db, admin_headers):
    """El guard es solo sobre `estado`: los demás campos siguen editables."""
    mesa, _ = _mesa_con_pedido(client, db, admin_headers, 906)
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"capacidad": 8},
    )
    assert r.status_code == 200
    assert r.json()["capacidad"] == 8


def test_mesa_editable_tras_cobrar(client, db, admin_headers, cajero_headers):
    from app.models import MetodoPago

    mesa, pedido = _mesa_con_pedido(client, db, admin_headers, 907)
    efectivo = (
        db.query(MetodoPago)
        .filter(MetodoPago.nombre_metodo == "Efectivo")
        .one()
        .id_metodo_pago
    )
    assert (
        client.post(
            "/api/v1/ventas",
            headers=cajero_headers,
            json={
                "id_pedido": pedido["id_pedido"],
                "pagos": [{"id_metodo_pago": efectivo, "monto": 200.0}],
            },
        ).status_code
        == 201
    )
    r = client.patch(
        f"/api/v1/mesas/{mesa['id_mesa']}",
        headers=admin_headers,
        json={"estado": "Reservada"},
    )
    assert r.status_code == 200
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `docker run --rm --network cafeteria-system_default --user $(id -u):$(id -g) --env-file <worktree>/.env -v <worktree>/backend:/code -w /code cafeteria-system-api pytest tests/test_mesas_api.py -v`
Expected: FAIL en `test_cambiar_estado_con_pedido_activo_409` (devuelve 200 en vez de 409) y en `test_marcar_ocupada_a_mano_422` (devuelve 200 en vez de 422). Los otros cinco ya deberían pasar: son el comportamiento que hay que conservar.

- [ ] **Step 3: Implementar el guard**

En `backend/app/services/mesa_service.py`, añadir el import del servicio bajo los imports existentes de `app.`:

```python
from app.services import pedido_service
```

Y reemplazar `update` por:

```python
def update(db: Session, id_mesa: int, data: MesaUpdate) -> Mesa:
    obj = get_or_404(db, id_mesa)
    if data.numero_mesa is not None:
        _ensure_unico(db, data.numero_mesa, exclude_id=id_mesa)
    if data.estado is not None and data.estado != obj.estado:
        # "Ocupada" no se asigna a mano: lo pone el sistema al crear un pedido y
        # lo quita el cobro o la cancelación.
        if data.estado == "Ocupada":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "El estado Ocupada lo asigna el sistema al crear un pedido",
            )
        # Se consulta el pedido real, no la bandera de la mesa: así una mesa que
        # quedó marcada Ocupada sin pedido activo se puede corregir.
        if pedido_service.tiene_pedido_activo(db, id_mesa):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "La mesa tiene un pedido activo; su estado lo gestiona el sistema",
            )
    for campo in ("numero_mesa", "capacidad", "ubicacion", "estado"):
        valor = getattr(data, campo)
        if valor is not None:
            setattr(obj, campo, valor)
    db.commit()
    db.refresh(obj)
    return obj
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `docker run --rm --network cafeteria-system_default --user $(id -u):$(id -g) --env-file <worktree>/.env -v <worktree>/backend:/code -w /code cafeteria-system-api pytest tests/test_mesas_api.py -v`
Expected: PASS — los tests previos del archivo más los 7 nuevos.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/mesa_service.py backend/tests/test_mesas_api.py
git commit -m "feat(api): bloquear el cambio de estado de una mesa con pedido activo"
```

---

### Task 3: Verificación integral y documentación

**Files:**
- Modify: `progress.md`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: bitácora actualizada; rama lista para PR.

- [ ] **Step 1: Suite completa del backend**

Run: `docker run --rm --network cafeteria-system_default --user $(id -u):$(id -g) --env-file <worktree>/.env -v <worktree>/backend:/code -w /code cafeteria-system-api pytest -q`
Expected: PASS — 206 previos + 4 (Task 1) + 7 (Task 2) = **217**, sin fallos.

Si algún test previo falla, PARAR y reportar: significa que el guard rompió un flujo existente (p. ej. algún test que liberaba una mesa por API). No arreglarlo por cuenta propia sin entender la causa.

- [ ] **Step 2: Verificar que la web sigue funcionando**

El panel no se tocó, pero su formulario de mesas hace PATCH contra esta ruta. Correr su suite:

Run: `docker compose exec web pytest -q`
Expected: PASS — 114 tests. (La web quita `estado` del payload cuando la mesa está Ocupada, así que no debería chocar con el guard.)

- [ ] **Step 3: Actualizar `progress.md`**

En la sección "Deuda técnica / mejoras conocidas", reemplazar cualquier mención al guard de Ocupada como pendiente y añadir:

```
- Guard de mesa Ocupada: la API rechaza cambiar el estado de una mesa con pedido activo (409) y asignar "Ocupada" a mano (422). La web mantiene su propio aviso mirando la bandera `mesa.estado`, así que en el caso raro de una mesa marcada Ocupada sin pedido activo el panel seguirá bloqueando el cambio aunque la API lo permita; destrabarla se hace por API.
```

En la sección "Próximo", registrar el slice terminado y dejar anotado que **el hardening CSRF del panel web sigue pendiente** como slice aparte. Actualizar la fecha y el resumen de "Última actualización" en la cabecera.

- [ ] **Step 4: Commit**

```bash
git add progress.md
git commit -m "docs: progress.md — guard de mesa Ocupada en la API"
```

- [ ] **Step 5: Abrir el PR**

```bash
git push -u origin feat/api-guard-ocupada
gh pr create --base main \
  --title "feat(api): guard de mesa Ocupada — el estado de una mesa con pedido activo lo gestiona el sistema" \
  --body "$(cat <<'EOF'
## Resumen

Cierra el pendiente diferido del review del PR #21: la regla "no cambies el estado de una mesa Ocupada" vivía **solo** en el panel web, así que por Swagger, curl o el móvil se podía liberar una mesa con un pedido activo — dejando el pedido abierto, la mesa marcada como libre y permitiendo tomar otro pedido sobre una mesa en uso.

- **Predicado único de "pedido activo"** (`pedido_service.condiciones_pedido_activo` / `tiene_pedido_activo`): ni cancelado ni cobrado. La regla estaba implícita dentro de `venta_service.listar_por_cobrar`, que ahora la consume en vez de repetirla.
- **Guard en `mesa_service.update`**: 409 si la mesa tiene un pedido activo, 422 si se intenta asignar `"Ocupada"` a mano. Solo se dispara si el estado cambia de verdad, así que reenviar el mismo valor no falla.
- **Se apoya en el pedido real, no en la bandera `mesa.estado`.** Calcar la regla de la web habría permitido marcar una mesa Ocupada a mano y dejarla **bloqueada sin salida**: `pedido_service.crear` exige `estado == "Disponible"`, así que no aceptaría pedidos ni podría cambiarse de estado.
- `numero_mesa`, `capacidad` y `ubicacion` siguen editables con la mesa ocupada: el guard es solo sobre `estado`.

## Test plan

- [x] Backend: 217 tests (206 previos + 4 del predicado + 7 del guard)
- [x] Web: 114 tests — el panel no se tocó y su formulario sigue funcionando contra la ruta
- [ ] Deuda menor anotada: la web mira la bandera y la API el pedido; en el caso raro de una mesa marcada Ocupada sin pedido activo, el panel seguirá bloqueando el cambio aunque la API lo permita

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
