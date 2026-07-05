# API de transiciones de estado — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir a la API de pedidos el avance de estado (Pendiente → En preparación → Listo → Entregado) con validación de flujo lineal y autorización por rol, más la cancelación con registro de motivo y liberación de mesa.

**Architecture:** Toda la lógica vive en `pedido_service.py` con un mapa `_FLUJO` como fuente única de verdad de transiciones y roles. Dos endpoints nuevos en `api/v1/pedidos.py` (`PATCH /{id}/estado`, `POST /{id}/cancelar`) delegan al service pasando el usuario autenticado; la comprobación de rol ocurre dentro del service porque el rol permitido depende de la transición concreta.

**Tech Stack:** FastAPI · SQLAlchemy · Pydantic v2 · PostgreSQL · pytest (en el contenedor Docker).

## Global Constraints

- Los tests corren dentro del contenedor: `docker compose exec api pytest ...` (requiere `docker compose up -d`).
- Sin migración Alembic: los 5 estados (`Pendiente`, `En preparación`, `Listo`, `Entregado`, `Cancelado`) y la tabla `cancelaciones` ya existen y están sembrados.
- Seguir patrones existentes: services lanzan `HTTPException(status.<CODE>, "mensaje")`; endpoints usan `Depends(get_current_user)`.
- El rol del usuario se lee de `usuario.rol.nombre_rol` (relationship ya cargada, `lazy="joined"`) — sin consultas extra ni `require_role` nuevo.
- Nombres de estado y rol se comparan por su string exacto en español (incluye la tilde de "En preparación").

---

### Task 1: Avance de estado (`PATCH /pedidos/{id}/estado`)

**Files:**
- Modify: `backend/app/schemas/pedido.py` (añadir `EstadoUpdate`)
- Modify: `backend/app/services/pedido_service.py` (añadir `_FLUJO`, `_estado_por_nombre`, `cambiar_estado`)
- Modify: `backend/app/api/v1/pedidos.py` (añadir endpoint PATCH)
- Modify: `backend/tests/conftest.py` (añadir fixtures `cocinero`, `cocinero_headers`)
- Test: `backend/tests/test_transiciones_api.py` (crear)

**Interfaces:**
- Consumes: `get_or_404(db, id_pedido) -> Pedido` (ya existe); `Usuario.rol.nombre_rol`; `EstadoPedido`, `Pedido` de `app.models`.
- Produces:
  - `pedido_service.cambiar_estado(db: Session, id_pedido: int, id_estado_destino: int, usuario: Usuario) -> Pedido`
  - `pedido_service._estado_por_nombre(db: Session, nombre: str) -> EstadoPedido`
  - `pedido_service._FLUJO: dict[str, tuple[str, set[str]]]`
  - Schema `EstadoUpdate` con campo `id_estado: int`
  - Endpoint `PATCH /api/v1/pedidos/{id_pedido}/estado` → `PedidoOut`

- [ ] **Step 1: Añadir fixtures de cocinero al conftest**

En `backend/tests/conftest.py`, tras las fixtures `mesero`/`mesero_headers`, añadir:

```python
@pytest.fixture()
def cocinero(db):
    return _crear_usuario(db, "cocinerotest", "cocinero.test@cafeteria.com", "Cocinero")


@pytest.fixture()
def cocinero_headers(client, cocinero):
    return _headers(client, "cocinero.test@cafeteria.com")
```

- [ ] **Step 2: Escribir el test del camino feliz (falla)**

Crear `backend/tests/test_transiciones_api.py`:

```python
def _mesa(client, admin_headers, numero):
    return client.post(
        "/api/v1/mesas",
        headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()


def _producto(client, db, admin_headers, precio=50.0):
    from app.models import Categoria

    cat = db.query(Categoria).first()
    return client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": "Item",
            "precio_venta": precio,
            "disponible": True,
        },
    ).json()


def _pedido_pendiente(client, db, admin_headers, numero):
    mesa = _mesa(client, admin_headers, numero)
    prod = _producto(client, db, admin_headers)
    return client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()


def _estado_id(db, nombre):
    from app.models import EstadoPedido

    return (
        db.query(EstadoPedido)
        .filter(EstadoPedido.nombre_estado == nombre)
        .one()
        .id_estado
    )


def _patch_estado(client, headers, id_pedido, nombre_destino, db):
    return client.patch(
        f"/api/v1/pedidos/{id_pedido}/estado",
        headers=headers,
        json={"id_estado": _estado_id(db, nombre_destino)},
    )


def test_flujo_feliz_completo(
    client, db, admin_headers, cocinero_headers, mesero_headers
):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=301)
    pid = pedido["id_pedido"]

    r1 = _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    assert r1.status_code == 200
    assert r1.json()["estado"]["nombre_estado"] == "En preparación"

    r2 = _patch_estado(client, cocinero_headers, pid, "Listo", db)
    assert r2.status_code == 200
    assert r2.json()["estado"]["nombre_estado"] == "Listo"

    r3 = _patch_estado(client, mesero_headers, pid, "Entregado", db)
    assert r3.status_code == 200
    assert r3.json()["estado"]["nombre_estado"] == "Entregado"
```

- [ ] **Step 3: Ejecutar el test para verificar que falla**

Run: `docker compose exec api pytest tests/test_transiciones_api.py::test_flujo_feliz_completo -v`
Expected: FAIL (404 en el PATCH — la ruta no existe todavía).

- [ ] **Step 4: Añadir el schema `EstadoUpdate`**

En `backend/app/schemas/pedido.py`, tras `PedidoCreate`, añadir:

```python
class EstadoUpdate(BaseModel):
    id_estado: int
```

- [ ] **Step 5: Añadir `_FLUJO`, `_estado_por_nombre` y `cambiar_estado` al service**

En `backend/app/services/pedido_service.py`, tras `_estado_pendiente`, añadir:

```python
# estado_origen -> (estado_destino permitido, {roles autorizados})
_FLUJO: dict[str, tuple[str, set[str]]] = {
    "Pendiente": ("En preparación", {"Cocinero", "Administrador"}),
    "En preparación": ("Listo", {"Cocinero", "Administrador"}),
    "Listo": ("Entregado", {"Mesero", "Administrador"}),
}


def _estado_por_nombre(db: Session, nombre: str) -> EstadoPedido:
    return db.execute(
        select(EstadoPedido).where(EstadoPedido.nombre_estado == nombre)
    ).scalar_one()


def cambiar_estado(
    db: Session, id_pedido: int, id_estado_destino: int, usuario
) -> Pedido:
    pedido = get_or_404(db, id_pedido)
    destino = db.get(EstadoPedido, id_estado_destino)
    if destino is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Estado inválido")

    transicion = _FLUJO.get(pedido.estado.nombre_estado)
    if transicion is None or destino.nombre_estado != transicion[0]:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Transición de estado no permitida"
        )

    _, roles = transicion
    if usuario.rol.nombre_rol not in roles:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para esta transición"
        )

    pedido.id_estado = destino.id_estado
    db.commit()
    db.refresh(pedido)
    return pedido
```

Nota: `Usuario` no se importa para el type hint (se deja sin anotar como en otras funciones del módulo) para no añadir imports; el objeto llega con `rol.nombre_rol` disponible.

- [ ] **Step 6: Añadir el endpoint PATCH**

En `backend/app/api/v1/pedidos.py`, actualizar el import de schemas y añadir el endpoint tras `crear`:

```python
from app.schemas.pedido import EstadoUpdate, PedidoCreate, PedidoOut
```

```python
@router.patch("/{id_pedido}/estado", response_model=PedidoOut)
def cambiar_estado(
    id_pedido: int,
    data: EstadoUpdate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.cambiar_estado(db, id_pedido, data.id_estado, current)
```

- [ ] **Step 7: Ejecutar el test del camino feliz (pasa)**

Run: `docker compose exec api pytest tests/test_transiciones_api.py::test_flujo_feliz_completo -v`
Expected: PASS.

- [ ] **Step 8: Escribir los tests de error (fallan)**

Añadir a `backend/tests/test_transiciones_api.py`:

```python
def test_rol_equivocado_avanzar_403(client, db, admin_headers, mesero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=302)
    # mesero no puede Pendiente -> En preparación (eso es de cocina)
    r = _patch_estado(client, mesero_headers, pedido["id_pedido"], "En preparación", db)
    assert r.status_code == 403


def test_rol_equivocado_entregar_403(
    client, db, admin_headers, cocinero_headers
):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=303)
    pid = pedido["id_pedido"]
    _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    _patch_estado(client, cocinero_headers, pid, "Listo", db)
    # cocinero no puede Listo -> Entregado (eso es del mesero)
    r = _patch_estado(client, cocinero_headers, pid, "Entregado", db)
    assert r.status_code == 403


def test_salto_de_estado_409(client, db, admin_headers, cocinero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=304)
    # Pendiente -> Listo (salta "En preparación")
    r = _patch_estado(client, cocinero_headers, pedido["id_pedido"], "Listo", db)
    assert r.status_code == 409


def test_retroceso_409(client, db, admin_headers, cocinero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=305)
    pid = pedido["id_pedido"]
    _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    # Listo -> ... intentar retroceder a En preparación desde En preparación no aplica;
    # probamos retroceso real: avanzar a Listo y volver a En preparación
    _patch_estado(client, cocinero_headers, pid, "Listo", db)
    r = _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    assert r.status_code == 409


def test_avanzar_terminal_409(
    client, db, admin_headers, cocinero_headers, mesero_headers
):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=306)
    pid = pedido["id_pedido"]
    _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    _patch_estado(client, cocinero_headers, pid, "Listo", db)
    _patch_estado(client, mesero_headers, pid, "Entregado", db)
    # Entregado es terminal: cualquier avance -> 409
    r = _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    assert r.status_code == 409


def test_avanzar_pedido_inexistente_404(client, db, cocinero_headers):
    r = client.patch(
        "/api/v1/pedidos/999999/estado",
        headers=cocinero_headers,
        json={"id_estado": _estado_id(db, "En preparación")},
    )
    assert r.status_code == 404


def test_avanzar_sin_token_401(client, db):
    r = client.patch(
        "/api/v1/pedidos/1/estado",
        json={"id_estado": _estado_id(db, "En preparación")},
    )
    assert r.status_code == 401
```

- [ ] **Step 9: Ejecutar toda la suite de transiciones (pasa)**

Run: `docker compose exec api pytest tests/test_transiciones_api.py -v`
Expected: PASS (los 8 tests de avance). La lógica del Step 5 ya cubre 403/409/404/401.

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas/pedido.py backend/app/services/pedido_service.py \
  backend/app/api/v1/pedidos.py backend/tests/conftest.py \
  backend/tests/test_transiciones_api.py
git commit -m "feat(api): avance de estado del pedido con flujo lineal y rol

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Cancelación (`POST /pedidos/{id}/cancelar`)

**Files:**
- Modify: `backend/app/schemas/pedido.py` (añadir `CancelacionCreate`)
- Modify: `backend/app/services/pedido_service.py` (añadir `_CANCELABLE_ROLES`, `_TERMINALES`, `cancelar`)
- Modify: `backend/app/api/v1/pedidos.py` (añadir endpoint POST)
- Test: `backend/tests/test_transiciones_api.py` (añadir casos)

**Interfaces:**
- Consumes: `get_or_404`, `_estado_por_nombre` (Task 1), modelo `Cancelacion` de `app.models`, `pedido.mesa` (relationship existente).
- Produces:
  - `pedido_service.cancelar(db: Session, id_pedido: int, motivo: str, usuario: Usuario) -> Pedido`
  - Schema `CancelacionCreate` con campo `motivo: str` (`min_length=1`)
  - Endpoint `POST /api/v1/pedidos/{id_pedido}/cancelar` → `PedidoOut`

- [ ] **Step 1: Escribir el test de cancelación OK (falla)**

Añadir a `backend/tests/test_transiciones_api.py`:

```python
def _cancelar(client, headers, id_pedido, motivo="Cliente se fue"):
    return client.post(
        f"/api/v1/pedidos/{id_pedido}/cancelar",
        headers=headers,
        json={"motivo": motivo},
    )


def test_cancelar_ok_libera_mesa_y_registra(client, db, admin_headers, mesero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=320)
    pid = pedido["id_pedido"]
    id_mesa = pedido["id_mesa"]

    r = _cancelar(client, mesero_headers, pid, motivo="Cliente se fue")
    assert r.status_code == 200
    assert r.json()["estado"]["nombre_estado"] == "Cancelado"

    # la mesa vuelve a Disponible
    m = client.get(f"/api/v1/mesas/{id_mesa}", headers=admin_headers).json()
    assert m["estado"] == "Disponible"

    # se registró la cancelación con el motivo
    from app.models import Cancelacion

    fila = (
        db.query(Cancelacion).filter(Cancelacion.id_pedido == pid).one()
    )
    assert fila.motivo == "Cliente se fue"
```

- [ ] **Step 2: Ejecutar el test para verificar que falla**

Run: `docker compose exec api pytest tests/test_transiciones_api.py::test_cancelar_ok_libera_mesa_y_registra -v`
Expected: FAIL (404 — la ruta no existe).

- [ ] **Step 3: Añadir el schema `CancelacionCreate`**

En `backend/app/schemas/pedido.py`, tras `EstadoUpdate`, añadir:

```python
class CancelacionCreate(BaseModel):
    motivo: str = Field(min_length=1)
```

`Field` ya está importado en el módulo.

- [ ] **Step 4: Añadir `cancelar` al service**

En `backend/app/services/pedido_service.py`, actualizar el import de modelos y añadir la lógica.

Import (añadir `Cancelacion`):

```python
from app.models import Cancelacion, DetallePedido, EstadoPedido, Mesa, Pedido, Producto
```

Tras `_FLUJO`, añadir las constantes:

```python
_CANCELABLE_ROLES = {"Mesero", "Administrador"}
_TERMINALES = {"Entregado", "Cancelado"}
```

Al final del archivo, añadir:

```python
def cancelar(db: Session, id_pedido: int, motivo: str, usuario) -> Pedido:
    pedido = get_or_404(db, id_pedido)
    if pedido.estado.nombre_estado in _TERMINALES:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "El pedido no se puede cancelar en su estado actual"
        )
    if usuario.rol.nombre_rol not in _CANCELABLE_ROLES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Rol no autorizado para cancelar"
        )

    db.add(
        Cancelacion(
            id_pedido=pedido.id_pedido,
            id_usuario=usuario.id_usuario,
            motivo=motivo,
        )
    )
    pedido.id_estado = _estado_por_nombre(db, "Cancelado").id_estado
    pedido.mesa.estado = "Disponible"
    db.commit()
    db.refresh(pedido)
    return pedido
```

- [ ] **Step 5: Añadir el endpoint POST**

En `backend/app/api/v1/pedidos.py`, actualizar el import y añadir el endpoint tras `cambiar_estado`:

```python
from app.schemas.pedido import (
    CancelacionCreate,
    EstadoUpdate,
    PedidoCreate,
    PedidoOut,
)
```

```python
@router.post("/{id_pedido}/cancelar", response_model=PedidoOut)
def cancelar(
    id_pedido: int,
    data: CancelacionCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.cancelar(db, id_pedido, data.motivo, current)
```

- [ ] **Step 6: Ejecutar el test de cancelación OK (pasa)**

Run: `docker compose exec api pytest tests/test_transiciones_api.py::test_cancelar_ok_libera_mesa_y_registra -v`
Expected: PASS.

- [ ] **Step 7: Escribir los tests de cancelación inválida (fallan/pasan)**

Añadir a `backend/tests/test_transiciones_api.py`:

```python
def test_cancelar_sin_motivo_422(client, db, admin_headers, mesero_headers):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=321)
    r = client.post(
        f"/api/v1/pedidos/{pedido['id_pedido']}/cancelar",
        headers=mesero_headers,
        json={"motivo": ""},
    )
    assert r.status_code == 422


def test_cancelar_entregado_409(
    client, db, admin_headers, cocinero_headers, mesero_headers
):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=322)
    pid = pedido["id_pedido"]
    _patch_estado(client, cocinero_headers, pid, "En preparación", db)
    _patch_estado(client, cocinero_headers, pid, "Listo", db)
    _patch_estado(client, mesero_headers, pid, "Entregado", db)
    r = _cancelar(client, mesero_headers, pid)
    assert r.status_code == 409


def test_cancelar_rol_no_autorizado_403(
    client, db, admin_headers, cocinero_headers
):
    pedido = _pedido_pendiente(client, db, admin_headers, numero=323)
    # el cocinero no puede cancelar
    r = _cancelar(client, cocinero_headers, pedido["id_pedido"])
    assert r.status_code == 403


def test_cancelar_pedido_inexistente_404(client, mesero_headers):
    r = client.post(
        "/api/v1/pedidos/999999/cancelar",
        headers=mesero_headers,
        json={"motivo": "x"},
    )
    assert r.status_code == 404
```

- [ ] **Step 8: Ejecutar toda la suite de transiciones (pasa)**

Run: `docker compose exec api pytest tests/test_transiciones_api.py -v`
Expected: PASS (todos: avance + cancelación).

- [ ] **Step 9: Ejecutar la suite completa del backend (sin regresiones)**

Run: `docker compose exec api pytest -q`
Expected: PASS (los 68 previos + los nuevos).

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas/pedido.py backend/app/services/pedido_service.py \
  backend/app/api/v1/pedidos.py backend/tests/test_transiciones_api.py
git commit -m "feat(api): cancelación de pedido con motivo y liberación de mesa

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notas de verificación final (tras Task 2)

- `docker compose exec api pytest -q` en verde.
- Revisar en Swagger (`localhost:8000/docs`) que aparecen `PATCH /pedidos/{id}/estado` y `POST /pedidos/{id}/cancelar`.
- Actualizar `progress.md` (marca del Sprint 3 slice 1) — se hace al cerrar el slice, no en este plan.
