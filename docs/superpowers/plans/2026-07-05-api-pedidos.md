# API de Pedidos (crear y consultar) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Crear pedidos con líneas (precio congelado, total derivado, mesa Disponible→Ocupada) y consultarlos.

**Architecture:** Router fino `/pedidos` delega en `pedido_service`; relaciones ORM y una propiedad `Pedido.total` (sin migración) dan una respuesta lista para el móvil. Sigue el patrón de catálogo.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, pytest.

## Global Constraints

- Tests en el contenedor: `docker compose exec -T api pytest ...`.
- Todos los endpoints requieren `deps.get_current_user`.
- Crear pedido: mesa debe estar **Disponible** (409 si no) → pasa a **Ocupada**; producto inexistente/`disponible=false` → 422; estado inicial **Pendiente**; `id_usuario` = usuario actual.
- **Precio congelado:** `detalle_pedido.precio_unitario` = `producto.precio_venta` al crear; el cliente no envía precios.
- `total` = Σ `detalle.subtotal` (propiedad del modelo; `subtotal` es columna generada).
- Prerrequisito cumplido: catálogo (slice 1) mergeado; estados_pedido sembrados (Pendiente…Cancelado).

---

### Task 1: Modelo (relaciones + total) y schemas

**Files:**
- Modify: `backend/app/models/pedido.py`
- Create: `backend/app/schemas/pedido.py`
- Test: `backend/tests/test_pedido_model.py`

**Interfaces:**
- Produces:
  - `Pedido.mesa`, `Pedido.estado`, `Pedido.detalle` (relaciones); `Pedido.total` (`@property -> Decimal`).
  - `DetallePedido.producto` (relación).
  - Schemas: `PedidoItemCreate`, `PedidoCreate`, `ProductoResumen`, `DetalleOut`,
    `MesaResumen`, `EstadoResumen`, `PedidoOut`.

- [ ] **Step 1: Escribir el test que falla**

```python
# backend/tests/test_pedido_model.py
from decimal import Decimal


def test_pedido_total_suma_subtotales(db, admin):
    from app.models import (
        Categoria, DetallePedido, EstadoPedido, Mesa, Pedido, Producto,
    )

    cat = db.query(Categoria).first()
    prod = Producto(
        id_categoria=cat.id_categoria, nombre_producto="X", precio_venta=10, disponible=True
    )
    mesa = Mesa(numero_mesa=555, capacidad=4)
    db.add_all([prod, mesa])
    db.flush()
    estado = db.query(EstadoPedido).filter(EstadoPedido.nombre_estado == "Pendiente").one()
    pedido = Pedido(
        id_mesa=mesa.id_mesa,
        id_usuario=admin.id_usuario,
        id_estado=estado.id_estado,
        detalle=[
            DetallePedido(id_producto=prod.id_producto, cantidad=2, precio_unitario=10),
            DetallePedido(id_producto=prod.id_producto, cantidad=1, precio_unitario=10),
        ],
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    assert pedido.total == Decimal("30.00")
    assert pedido.detalle[0].producto.nombre_producto == "X"
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `docker compose exec -T api pytest tests/test_pedido_model.py -v`
Expected: FAIL (AttributeError: 'Pedido' object has no attribute 'total' / 'detalle').

- [ ] **Step 3: Añadir relaciones y `total` en `models/pedido.py`**

Cambiar el import de sqlalchemy.orm y añadir relaciones. En la cabecera:

```python
from decimal import Decimal

from sqlalchemy.orm import relationship
```

En la clase `Pedido`, tras `observaciones`:

```python
    mesa = relationship("Mesa", lazy="joined")
    estado = relationship("EstadoPedido", lazy="joined")
    detalle = relationship(
        "DetallePedido", lazy="selectin", cascade="all, delete-orphan"
    )

    @property
    def total(self) -> Decimal:
        return sum((d.subtotal for d in self.detalle), Decimal("0"))
```

En la clase `DetallePedido`, tras `observaciones`:

```python
    producto = relationship("Producto", lazy="joined")
```

- [ ] **Step 4: Implementar `schemas/pedido.py`**

```python
# backend/app/schemas/pedido.py
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PedidoItemCreate(BaseModel):
    id_producto: int
    cantidad: int = Field(ge=1)
    observaciones: str | None = None


class PedidoCreate(BaseModel):
    id_mesa: int
    observaciones: str | None = None
    items: list[PedidoItemCreate] = Field(min_length=1)


class ProductoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    nombre_producto: str


class DetalleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_detalle: int
    id_producto: int
    producto: ProductoResumen
    cantidad: int
    precio_unitario: Decimal
    subtotal: Decimal
    observaciones: str | None


class MesaResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_mesa: int
    numero_mesa: int


class EstadoResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_estado: int
    nombre_estado: str


class PedidoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_pedido: int
    id_mesa: int
    mesa: MesaResumen
    id_estado: int
    estado: EstadoResumen
    id_usuario: int
    fecha_pedido: datetime
    observaciones: str | None
    detalle: list[DetalleOut]
    total: Decimal
```

- [ ] **Step 5: Correr y verificar que pasa (y no romper la suite)**

Run: `docker compose exec -T api pytest tests/test_pedido_model.py -q && docker compose exec -T api pytest -q`
Expected: PASS (nuevo test + toda la suite del slice 1).

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/pedido.py backend/app/schemas/pedido.py backend/tests/test_pedido_model.py
git commit -m "feat(api): relaciones y total en Pedido + schemas de pedido"
```

---

### Task 2: Crear pedido (service + POST)

**Files:**
- Create: `backend/app/services/pedido_service.py`
- Create: `backend/app/api/v1/pedidos.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_pedidos_api.py`

**Interfaces:**
- Consumes: schemas de pedido, modelos `Mesa/Producto/EstadoPedido/Pedido/DetallePedido`.
- Produces: `pedido_service.crear(db, data, id_usuario) -> Pedido`,
  `pedido_service.get_or_404(db, id_pedido) -> Pedido`,
  `pedido_service.list_pedidos(db, id_estado=None, id_usuario=None) -> list[Pedido]`.
  Endpoint `POST /api/v1/pedidos`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# backend/tests/test_pedidos_api.py
def _mesa(client, admin_headers, numero=201):
    return client.post(
        "/api/v1/mesas", headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()


def _producto(client, db, admin_headers, precio=50.0, disponible=True):
    from app.models import Categoria
    cat = db.query(Categoria).first()
    return client.post(
        "/api/v1/productos", headers=admin_headers,
        json={"id_categoria": cat.id_categoria, "nombre_producto": "Item",
              "precio_venta": precio, "disponible": disponible},
    ).json()


def test_crear_pedido_ok(client, db, admin_headers):
    mesa = _mesa(client, admin_headers)
    prod = _producto(client, db, admin_headers, precio=50.0)
    r = client.post("/api/v1/pedidos", headers=admin_headers, json={
        "id_mesa": mesa["id_mesa"], "observaciones": "Rápido",
        "items": [{"id_producto": prod["id_producto"], "cantidad": 2, "observaciones": None}],
    })
    assert r.status_code == 201
    body = r.json()
    assert float(body["total"]) == 100.0
    assert body["estado"]["nombre_estado"] == "Pendiente"
    # la mesa quedó Ocupada
    m = client.get(f"/api/v1/mesas/{mesa['id_mesa']}", headers=admin_headers).json()
    assert m["estado"] == "Ocupada"


def test_precio_congelado(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=202)
    prod = _producto(client, db, admin_headers, precio=50.0)
    pedido = client.post("/api/v1/pedidos", headers=admin_headers, json={
        "id_mesa": mesa["id_mesa"],
        "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
    }).json()
    # el detalle guarda el precio del producto al momento de crear
    assert float(pedido["detalle"][0]["precio_unitario"]) == 50.0


def test_mesa_ocupada_409(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=203)
    prod = _producto(client, db, admin_headers)
    payload = {"id_mesa": mesa["id_mesa"], "items": [{"id_producto": prod["id_producto"], "cantidad": 1}]}
    assert client.post("/api/v1/pedidos", headers=admin_headers, json=payload).status_code == 201
    assert client.post("/api/v1/pedidos", headers=admin_headers, json=payload).status_code == 409


def test_producto_no_disponible_422(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=204)
    prod = _producto(client, db, admin_headers, disponible=False)
    r = client.post("/api/v1/pedidos", headers=admin_headers, json={
        "id_mesa": mesa["id_mesa"], "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
    })
    assert r.status_code == 422


def test_sin_items_422(client, admin_headers):
    mesa = _mesa(client, admin_headers, numero=205)
    r = client.post("/api/v1/pedidos", headers=admin_headers, json={"id_mesa": mesa["id_mesa"], "items": []})
    assert r.status_code == 422


def test_sin_token_401(client):
    assert client.post("/api/v1/pedidos", json={"id_mesa": 1, "items": []}).status_code == 401
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `docker compose exec -T api pytest tests/test_pedidos_api.py -v`
Expected: FAIL (404/route).

- [ ] **Step 3: Implementar `services/pedido_service.py`**

```python
# backend/app/services/pedido_service.py
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DetallePedido, EstadoPedido, Mesa, Pedido, Producto
from app.schemas.pedido import PedidoCreate


def _estado_pendiente(db: Session) -> EstadoPedido:
    return db.execute(
        select(EstadoPedido).where(EstadoPedido.nombre_estado == "Pendiente")
    ).scalar_one()


def get_or_404(db: Session, id_pedido: int) -> Pedido:
    obj = db.get(Pedido, id_pedido)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido no encontrado")
    return obj


def list_pedidos(
    db: Session, id_estado: int | None = None, id_usuario: int | None = None
) -> list[Pedido]:
    stmt = select(Pedido).order_by(Pedido.id_pedido.desc())
    if id_estado is not None:
        stmt = stmt.where(Pedido.id_estado == id_estado)
    if id_usuario is not None:
        stmt = stmt.where(Pedido.id_usuario == id_usuario)
    return list(db.execute(stmt).scalars())


def crear(db: Session, data: PedidoCreate, id_usuario: int) -> Pedido:
    mesa = db.get(Mesa, data.id_mesa)
    if mesa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    if mesa.estado != "Disponible":
        raise HTTPException(status.HTTP_409_CONFLICT, "La mesa no está disponible")

    lineas = []
    for item in data.items:
        prod = db.get(Producto, item.id_producto)
        if prod is None or not prod.disponible:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"El producto {item.id_producto} no está disponible",
            )
        lineas.append(
            DetallePedido(
                id_producto=prod.id_producto,
                cantidad=item.cantidad,
                precio_unitario=prod.precio_venta,
                observaciones=item.observaciones,
            )
        )

    pedido = Pedido(
        id_mesa=mesa.id_mesa,
        id_usuario=id_usuario,
        id_estado=_estado_pendiente(db).id_estado,
        observaciones=data.observaciones,
        detalle=lineas,
    )
    mesa.estado = "Ocupada"
    db.add(pedido)
    db.commit()
    db.refresh(pedido)
    return pedido
```

- [ ] **Step 4: Implementar `api/v1/pedidos.py`**

```python
# backend/app/api/v1/pedidos.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.pedido import PedidoCreate, PedidoOut
from app.services import pedido_service

router = APIRouter(prefix="/pedidos", tags=["pedidos"])


@router.post("", response_model=PedidoOut, status_code=status.HTTP_201_CREATED)
def crear(
    data: PedidoCreate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.crear(db, data, current.id_usuario)
```

- [ ] **Step 5: Registrar el router en `api/v1/router.py`**

```python
from app.api.v1 import auth, categorias, mesas, pedidos, productos, roles, usuarios
# ...
api_router.include_router(pedidos.router)
```

- [ ] **Step 6: Correr y verificar que pasan**

Run: `docker compose exec -T api pytest tests/test_pedidos_api.py -v`
Expected: PASS (6 tests).

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/pedido_service.py backend/app/api/v1/pedidos.py backend/app/api/v1/router.py backend/tests/test_pedidos_api.py
git commit -m "feat(api): crear pedido (precio congelado, mesa->Ocupada, total)"
```

---

### Task 3: Consultar pedidos (GET lista + detalle)

**Files:**
- Modify: `backend/app/api/v1/pedidos.py`
- Test: `backend/tests/test_pedidos_api.py` (añadir)

**Interfaces:**
- Consumes: `pedido_service.list_pedidos/get_or_404`.
- Produces: `GET /api/v1/pedidos` (`?id_estado=` `&mias=true`), `GET /api/v1/pedidos/{id}`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `backend/tests/test_pedidos_api.py`:

```python
def test_detalle_trae_lineas_y_total(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=210)
    prod = _producto(client, db, admin_headers, precio=20.0)
    creado = client.post("/api/v1/pedidos", headers=admin_headers, json={
        "id_mesa": mesa["id_mesa"],
        "items": [{"id_producto": prod["id_producto"], "cantidad": 3}],
    }).json()
    r = client.get(f"/api/v1/pedidos/{creado['id_pedido']}", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert float(body["total"]) == 60.0
    assert body["detalle"][0]["producto"]["nombre_producto"] == "Item"


def test_listar_mias(client, db, admin, admin_headers, mesero, mesero_headers):
    # el admin crea un pedido; el mesero pide "mías" y no debe verlo
    mesa = _mesa(client, admin_headers, numero=211)
    prod = _producto(client, db, admin_headers)
    admin_pedido = client.post("/api/v1/pedidos", headers=admin_headers, json={
        "id_mesa": mesa["id_mesa"], "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
    }).json()
    mias_del_mesero = client.get("/api/v1/pedidos?mias=true", headers=mesero_headers).json()
    assert all(p["id_pedido"] != admin_pedido["id_pedido"] for p in mias_del_mesero)
    # el admin sí lo ve en sus "mías"
    mias_del_admin = client.get("/api/v1/pedidos?mias=true", headers=admin_headers).json()
    assert any(p["id_pedido"] == admin_pedido["id_pedido"] for p in mias_del_admin)


def test_precio_persiste_tras_cambiar_producto(client, db, admin_headers):
    mesa = _mesa(client, admin_headers, numero=212)
    prod = _producto(client, db, admin_headers, precio=50.0)
    creado = client.post("/api/v1/pedidos", headers=admin_headers, json={
        "id_mesa": mesa["id_mesa"], "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
    }).json()
    client.patch(f"/api/v1/productos/{prod['id_producto']}", headers=admin_headers,
                 json={"precio_venta": 99.0})
    r = client.get(f"/api/v1/pedidos/{creado['id_pedido']}", headers=admin_headers).json()
    assert float(r["detalle"][0]["precio_unitario"]) == 50.0


def test_detalle_inexistente_404(client, admin_headers):
    assert client.get("/api/v1/pedidos/999999", headers=admin_headers).status_code == 404
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `docker compose exec -T api pytest tests/test_pedidos_api.py::test_detalle_trae_lineas_y_total -v`
Expected: FAIL (404 en la ruta GET /{id}).

- [ ] **Step 3: Añadir los endpoints GET en `api/v1/pedidos.py`**

Añadir tras el `POST` (mantener los imports; añadir `Usuario` ya está):

```python
@router.get("", response_model=list[PedidoOut])
def listar(
    id_estado: int | None = None,
    mias: bool = False,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    id_usuario = current.id_usuario if mias else None
    return pedido_service.list_pedidos(db, id_estado, id_usuario)


@router.get("/{id_pedido}", response_model=PedidoOut)
def detalle(
    id_pedido: int,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return pedido_service.get_or_404(db, id_pedido)
```

- [ ] **Step 4: Correr y verificar que pasan**

Run: `docker compose exec -T api pytest tests/test_pedidos_api.py -v`
Expected: PASS (9 tests en el archivo).

- [ ] **Step 5: Correr toda la suite**

Run: `docker compose exec -T api pytest -q`
Expected: PASS (todas: slice 1 + pedidos).

- [ ] **Step 6: Verificación manual por HTTP**

```bash
ACCESS=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -d "username=admin@cafeteria.com&password=cambiar_en_local" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
# usar una mesa Disponible y un producto sembrados
curl -s -X POST http://localhost:8000/api/v1/pedidos -H "Authorization: Bearer $ACCESS" -H "Content-Type: application/json" \
  -d '{"id_mesa": 1, "items": [{"id_producto": 1, "cantidad": 2}]}' | python3 -m json.tool | head -30
```
Expected: 201 con `total`, `estado.nombre_estado=Pendiente`, y la mesa 1 luego `Ocupada`.
(Nota: si la mesa 1 ya quedó Ocupada por una prueba previa, usar otra mesa Disponible.)

- [ ] **Step 7: Commit**

```bash
git add backend/app/api/v1/pedidos.py backend/tests/test_pedidos_api.py
git commit -m "feat(api): listar y consultar pedidos (filtro mias, detalle con total)"
```

---

## Cierre

- [ ] Push: `git push -u origin feature/api-pedidos`
- [ ] Abrir PR hacia `main`.

## Self-Review (cobertura del spec)

- Crear pedido con líneas + observaciones → Task 2. ✅
- Precio congelado desde el server → Task 2 (test dedicado). ✅
- Mesa Disponible→Ocupada, 409 si no → Task 2. ✅
- Producto no disponible/inexistente → 422 → Task 2. ✅
- items vacío / cantidad<1 → 422 (schema) → Task 2. ✅
- Total derivado (propiedad) → Task 1 (test) + expuesto en `PedidoOut`. ✅
- GET lista con `?mias=` y `?id_estado=` → Task 3. ✅
- GET detalle con líneas + producto + total → Task 3. ✅
- 401 sin token, 404 inexistente → Tasks 2, 3. ✅
- Relaciones ORM (mesa/estado/detalle/producto) → Task 1. ✅
- Fuera de alcance (transiciones estado, cancelación, cobro, inventario, móvil): ausente. ✅
