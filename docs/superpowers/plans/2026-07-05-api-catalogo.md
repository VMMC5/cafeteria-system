# API de Catálogo (mesas, categorías, productos) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Endpoints CRUD de mesas, categorías y productos en la API, con lectura para autenticados y escritura para admin, borrado FK-safe, y seed de ejemplo.

**Architecture:** Routers finos bajo `/api/v1` delegan en un service por entidad; los services contienen las reglas (unicidad, FK, soft-delete). Sigue el patrón de `usuarios`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, pytest.

## Global Constraints

- Tests en el contenedor: `docker compose exec -T api pytest ...`.
- Autorización: **GET → `deps.get_current_user`**, **POST/PATCH/DELETE → `deps.require_admin`**.
- Borrado: productos → soft (`disponible=false`); categorías/mesas → 409 si referenciadas, si no borra (204).
- `estado` de mesa ∈ {Disponible, Ocupada, Reservada}; `precio_venta` ≥ 0; `capacidad` ≥ 1.
- `ProductoOut` incluye `categoria` anidada.
- Prerrequisito ya cumplido: catálogos base sembrados (categorías Bebidas/Comidas/Postres, estados_pedido) y admin.

---

### Task 1: Categorías (CRUD)

**Files:**
- Create: `backend/app/schemas/categoria.py`
- Create: `backend/app/services/categoria_service.py`
- Create: `backend/app/api/v1/categorias.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_categorias_api.py`

**Interfaces:**
- Produces: `CategoriaOut(id_categoria, nombre_categoria, descripcion)`;
  `categoria_service.get_or_404/list_categorias/create/update/delete`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# backend/tests/test_categorias_api.py
def _nueva():
    return {"nombre_categoria": "Snacks", "descripcion": "Botanas"}


def test_listar_requiere_auth(client):
    assert client.get("/api/v1/categorias").status_code == 401


def test_listar_autenticado(client, mesero_headers):
    r = client.get("/api/v1/categorias", headers=mesero_headers)
    assert r.status_code == 200
    assert any(c["nombre_categoria"] == "Bebidas" for c in r.json())


def test_crear_requiere_admin(client, mesero_headers):
    assert client.post("/api/v1/categorias", headers=mesero_headers, json=_nueva()).status_code == 403


def test_crear_y_duplicado(client, admin_headers):
    r = client.post("/api/v1/categorias", headers=admin_headers, json=_nueva())
    assert r.status_code == 201
    assert client.post("/api/v1/categorias", headers=admin_headers, json=_nueva()).status_code == 409


def test_editar(client, admin_headers):
    creada = client.post("/api/v1/categorias", headers=admin_headers, json=_nueva()).json()
    r = client.patch(f"/api/v1/categorias/{creada['id_categoria']}", headers=admin_headers,
                     json={"descripcion": "Actualizada"})
    assert r.status_code == 200 and r.json()["descripcion"] == "Actualizada"


def test_borrar_vacia_204(client, admin_headers):
    creada = client.post("/api/v1/categorias", headers=admin_headers, json=_nueva()).json()
    assert client.delete(f"/api/v1/categorias/{creada['id_categoria']}", headers=admin_headers).status_code == 204
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `docker compose exec -T api pytest tests/test_categorias_api.py -v`
Expected: FAIL (404 en las rutas).

- [ ] **Step 3: Implementar `schemas/categoria.py`**

```python
# backend/app/schemas/categoria.py
from pydantic import BaseModel, ConfigDict


class CategoriaCreate(BaseModel):
    nombre_categoria: str
    descripcion: str | None = None


class CategoriaUpdate(BaseModel):
    nombre_categoria: str | None = None
    descripcion: str | None = None


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_categoria: int
    nombre_categoria: str
    descripcion: str | None
```

- [ ] **Step 4: Implementar `services/categoria_service.py`**

```python
# backend/app/services/categoria_service.py
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Categoria, Producto
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate


def list_categorias(db: Session) -> list[Categoria]:
    return list(db.execute(select(Categoria).order_by(Categoria.id_categoria)).scalars())


def get_or_404(db: Session, id_categoria: int) -> Categoria:
    obj = db.get(Categoria, id_categoria)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    return obj


def _ensure_unico(db: Session, nombre: str, exclude_id: int | None = None) -> None:
    existing = db.execute(
        select(Categoria).where(Categoria.nombre_categoria == nombre)
    ).scalar_one_or_none()
    if existing is not None and existing.id_categoria != exclude_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "La categoría ya existe")


def create(db: Session, data: CategoriaCreate) -> Categoria:
    _ensure_unico(db, data.nombre_categoria)
    obj = Categoria(nombre_categoria=data.nombre_categoria, descripcion=data.descripcion)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, id_categoria: int, data: CategoriaUpdate) -> Categoria:
    obj = get_or_404(db, id_categoria)
    if data.nombre_categoria is not None:
        _ensure_unico(db, data.nombre_categoria, exclude_id=id_categoria)
        obj.nombre_categoria = data.nombre_categoria
    if data.descripcion is not None:
        obj.descripcion = data.descripcion
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, id_categoria: int) -> None:
    obj = get_or_404(db, id_categoria)
    tiene_productos = db.execute(
        select(Producto).where(Producto.id_categoria == id_categoria)
    ).first()
    if tiene_productos:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "La categoría tiene productos asociados"
        )
    db.delete(obj)
    db.commit()
```

- [ ] **Step 5: Implementar `api/v1/categorias.py`**

```python
# backend/app/api/v1/categorias.py
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.categoria import CategoriaCreate, CategoriaOut, CategoriaUpdate
from app.services import categoria_service

router = APIRouter(prefix="/categorias", tags=["categorias"])


@router.get("", response_model=list[CategoriaOut])
def listar(db: Session = Depends(get_db), _: Usuario = Depends(deps.get_current_user)):
    return categoria_service.list_categorias(db)


@router.get("/{id_categoria}", response_model=CategoriaOut)
def detalle(id_categoria: int, db: Session = Depends(get_db), _: Usuario = Depends(deps.get_current_user)):
    return categoria_service.get_or_404(db, id_categoria)


@router.post("", response_model=CategoriaOut, status_code=status.HTTP_201_CREATED)
def crear(data: CategoriaCreate, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return categoria_service.create(db, data)


@router.patch("/{id_categoria}", response_model=CategoriaOut)
def editar(id_categoria: int, data: CategoriaUpdate, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return categoria_service.update(db, id_categoria, data)


@router.delete("/{id_categoria}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(id_categoria: int, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    categoria_service.delete(db, id_categoria)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 6: Registrar el router en `api/v1/router.py`**

```python
# backend/app/api/v1/router.py
from fastapi import APIRouter

from app.api.v1 import auth, categorias, roles, usuarios

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(usuarios.router)
api_router.include_router(roles.router)
api_router.include_router(categorias.router)
```

- [ ] **Step 7: Correr y verificar que pasan**

Run: `docker compose exec -T api pytest tests/test_categorias_api.py -v`
Expected: PASS (6 tests).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/categoria.py backend/app/services/categoria_service.py backend/app/api/v1/categorias.py backend/app/api/v1/router.py backend/tests/test_categorias_api.py
git commit -m "feat(api): CRUD de categorias (lectura auth, escritura admin, delete FK-safe)"
```

---

### Task 2: Mesas (CRUD)

**Files:**
- Create: `backend/app/schemas/mesa.py`
- Create: `backend/app/services/mesa_service.py`
- Create: `backend/app/api/v1/mesas.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_mesas_api.py`

**Interfaces:**
- Produces: `MesaOut(id_mesa, numero_mesa, capacidad, ubicacion, estado)`;
  `mesa_service.get_or_404/list_mesas/create/update/delete`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# backend/tests/test_mesas_api.py
def _nueva(**over):
    base = {"numero_mesa": 101, "capacidad": 4, "ubicacion": "Terraza"}
    base.update(over)
    return base


def test_listar_autenticado(client, mesero_headers):
    assert client.get("/api/v1/mesas", headers=mesero_headers).status_code == 200


def test_listar_sin_token_401(client):
    assert client.get("/api/v1/mesas").status_code == 401


def test_crear_requiere_admin(client, mesero_headers):
    assert client.post("/api/v1/mesas", headers=mesero_headers, json=_nueva()).status_code == 403


def test_crear_y_duplicado(client, admin_headers):
    assert client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).status_code == 201
    assert client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).status_code == 409


def test_estado_invalido_422(client, admin_headers):
    assert client.post("/api/v1/mesas", headers=admin_headers, json=_nueva(estado="Rota")).status_code == 422


def test_capacidad_invalida_422(client, admin_headers):
    assert client.post("/api/v1/mesas", headers=admin_headers, json=_nueva(capacidad=0)).status_code == 422


def test_editar_estado(client, admin_headers):
    creada = client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).json()
    r = client.patch(f"/api/v1/mesas/{creada['id_mesa']}", headers=admin_headers, json={"estado": "Ocupada"})
    assert r.status_code == 200 and r.json()["estado"] == "Ocupada"


def test_borrar_sin_pedidos_204(client, admin_headers):
    creada = client.post("/api/v1/mesas", headers=admin_headers, json=_nueva()).json()
    assert client.delete(f"/api/v1/mesas/{creada['id_mesa']}", headers=admin_headers).status_code == 204


def test_borrar_con_pedido_409(client, db, admin, admin_headers):
    from app.models import EstadoPedido, Pedido

    creada = client.post("/api/v1/mesas", headers=admin_headers, json=_nueva(numero_mesa=102)).json()
    estado = db.query(EstadoPedido).first()
    db.add(Pedido(id_mesa=creada["id_mesa"], id_usuario=admin.id_usuario, id_estado=estado.id_estado))
    db.flush()
    assert client.delete(f"/api/v1/mesas/{creada['id_mesa']}", headers=admin_headers).status_code == 409
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `docker compose exec -T api pytest tests/test_mesas_api.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Implementar `schemas/mesa.py`**

```python
# backend/app/schemas/mesa.py
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

EstadoMesa = Literal["Disponible", "Ocupada", "Reservada"]


class MesaCreate(BaseModel):
    numero_mesa: int
    capacidad: int = Field(ge=1)
    ubicacion: str | None = None
    estado: EstadoMesa = "Disponible"


class MesaUpdate(BaseModel):
    numero_mesa: int | None = None
    capacidad: int | None = Field(default=None, ge=1)
    ubicacion: str | None = None
    estado: EstadoMesa | None = None


class MesaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_mesa: int
    numero_mesa: int
    capacidad: int
    ubicacion: str | None
    estado: str
```

- [ ] **Step 4: Implementar `services/mesa_service.py`**

```python
# backend/app/services/mesa_service.py
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Mesa, Pedido
from app.schemas.mesa import MesaCreate, MesaUpdate


def list_mesas(db: Session, estado: str | None = None) -> list[Mesa]:
    stmt = select(Mesa).order_by(Mesa.numero_mesa)
    if estado:
        stmt = stmt.where(Mesa.estado == estado)
    return list(db.execute(stmt).scalars())


def get_or_404(db: Session, id_mesa: int) -> Mesa:
    obj = db.get(Mesa, id_mesa)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Mesa no encontrada")
    return obj


def _ensure_unico(db: Session, numero: int, exclude_id: int | None = None) -> None:
    existing = db.execute(
        select(Mesa).where(Mesa.numero_mesa == numero)
    ).scalar_one_or_none()
    if existing is not None and existing.id_mesa != exclude_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "El número de mesa ya existe")


def create(db: Session, data: MesaCreate) -> Mesa:
    _ensure_unico(db, data.numero_mesa)
    obj = Mesa(
        numero_mesa=data.numero_mesa,
        capacidad=data.capacidad,
        ubicacion=data.ubicacion,
        estado=data.estado,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, id_mesa: int, data: MesaUpdate) -> Mesa:
    obj = get_or_404(db, id_mesa)
    if data.numero_mesa is not None:
        _ensure_unico(db, data.numero_mesa, exclude_id=id_mesa)
    for campo in ("numero_mesa", "capacidad", "ubicacion", "estado"):
        valor = getattr(data, campo)
        if valor is not None:
            setattr(obj, campo, valor)
    db.commit()
    db.refresh(obj)
    return obj


def delete(db: Session, id_mesa: int) -> None:
    obj = get_or_404(db, id_mesa)
    tiene_pedidos = db.execute(
        select(Pedido).where(Pedido.id_mesa == id_mesa)
    ).first()
    if tiene_pedidos:
        raise HTTPException(status.HTTP_409_CONFLICT, "La mesa tiene pedidos asociados")
    db.delete(obj)
    db.commit()
```

- [ ] **Step 5: Implementar `api/v1/mesas.py`**

```python
# backend/app/api/v1/mesas.py
from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.mesa import MesaCreate, MesaOut, MesaUpdate
from app.services import mesa_service

router = APIRouter(prefix="/mesas", tags=["mesas"])


@router.get("", response_model=list[MesaOut])
def listar(estado: str | None = None, db: Session = Depends(get_db), _: Usuario = Depends(deps.get_current_user)):
    return mesa_service.list_mesas(db, estado)


@router.get("/{id_mesa}", response_model=MesaOut)
def detalle(id_mesa: int, db: Session = Depends(get_db), _: Usuario = Depends(deps.get_current_user)):
    return mesa_service.get_or_404(db, id_mesa)


@router.post("", response_model=MesaOut, status_code=status.HTTP_201_CREATED)
def crear(data: MesaCreate, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return mesa_service.create(db, data)


@router.patch("/{id_mesa}", response_model=MesaOut)
def editar(id_mesa: int, data: MesaUpdate, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return mesa_service.update(db, id_mesa, data)


@router.delete("/{id_mesa}", status_code=status.HTTP_204_NO_CONTENT)
def borrar(id_mesa: int, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    mesa_service.delete(db, id_mesa)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

- [ ] **Step 6: Registrar el router en `api/v1/router.py`**

Añadir `mesas` al import y `api_router.include_router(mesas.router)`:

```python
from app.api.v1 import auth, categorias, mesas, roles, usuarios
# ...
api_router.include_router(mesas.router)
```

- [ ] **Step 7: Correr y verificar que pasan**

Run: `docker compose exec -T api pytest tests/test_mesas_api.py -v`
Expected: PASS (9 tests).

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/mesa.py backend/app/services/mesa_service.py backend/app/api/v1/mesas.py backend/app/api/v1/router.py backend/tests/test_mesas_api.py
git commit -m "feat(api): CRUD de mesas con estado validado y delete FK-safe"
```

---

### Task 3: Productos (CRUD + categoría anidada)

**Files:**
- Modify: `backend/app/models/producto.py` (relationship `categoria`)
- Create: `backend/app/schemas/producto.py`
- Create: `backend/app/services/producto_service.py`
- Create: `backend/app/api/v1/productos.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_productos_api.py`

**Interfaces:**
- Consumes: `CategoriaOut`.
- Produces: `ProductoOut` (con `categoria` anidada); `producto_service.get_or_404/list_productos/create/update/soft_delete`.

- [ ] **Step 1: Escribir los tests que fallan**

```python
# backend/tests/test_productos_api.py
def _cat_id(db, nombre="Bebidas"):
    from app.models import Categoria
    return db.query(Categoria).filter(Categoria.nombre_categoria == nombre).one().id_categoria


def _nuevo(db, **over):
    base = {
        "id_categoria": _cat_id(db),
        "nombre_producto": "Té Verde",
        "descripcion": "Caliente",
        "precio_venta": 35.0,
        "disponible": True,
    }
    base.update(over)
    return base


def test_crear_requiere_admin(client, db, mesero_headers):
    assert client.post("/api/v1/productos", headers=mesero_headers, json=_nuevo(db)).status_code == 403


def test_crear_devuelve_categoria_anidada(client, db, admin_headers):
    r = client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db))
    assert r.status_code == 201
    assert r.json()["categoria"]["nombre_categoria"] == "Bebidas"
    assert float(r.json()["precio_venta"]) == 35.0


def test_precio_negativo_422(client, db, admin_headers):
    assert client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db, precio_venta=-1)).status_code == 422


def test_categoria_inexistente_422(client, db, admin_headers):
    assert client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db, id_categoria=99999)).status_code == 422


def test_listar_filtra_por_categoria(client, db, admin_headers, mesero_headers):
    client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db))
    cat = _cat_id(db)
    r = client.get(f"/api/v1/productos?id_categoria={cat}", headers=mesero_headers)
    assert r.status_code == 200
    assert all(p["id_categoria"] == cat for p in r.json())


def test_soft_delete_sale_del_menu(client, db, admin_headers):
    creado = client.post("/api/v1/productos", headers=admin_headers, json=_nuevo(db)).json()
    r = client.delete(f"/api/v1/productos/{creado['id_producto']}", headers=admin_headers)
    assert r.status_code == 200 and r.json()["disponible"] is False
    # ya no aparece en el menú (disponible=true)
    menu = client.get("/api/v1/productos?disponible=true", headers=admin_headers).json()
    assert all(p["id_producto"] != creado["id_producto"] for p in menu)
```

- [ ] **Step 2: Correr y verificar que fallan**

Run: `docker compose exec -T api pytest tests/test_productos_api.py -v`
Expected: FAIL (404 / import).

- [ ] **Step 3: Añadir la relación al modelo `producto.py`**

Añadir el import y la relación en la clase `Producto` (tras `fecha_registro`):

```python
from sqlalchemy.orm import relationship
```

```python
    categoria = relationship("Categoria", lazy="joined")
```

- [ ] **Step 4: Implementar `schemas/producto.py`**

```python
# backend/app/schemas/producto.py
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.categoria import CategoriaOut


class ProductoCreate(BaseModel):
    id_categoria: int
    nombre_producto: str
    descripcion: str | None = None
    precio_venta: Decimal = Field(ge=0)
    disponible: bool = True


class ProductoUpdate(BaseModel):
    id_categoria: int | None = None
    nombre_producto: str | None = None
    descripcion: str | None = None
    precio_venta: Decimal | None = Field(default=None, ge=0)
    disponible: bool | None = None


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_producto: int
    id_categoria: int
    nombre_producto: str
    descripcion: str | None
    precio_venta: Decimal
    disponible: bool
    fecha_registro: datetime
    categoria: CategoriaOut
```

- [ ] **Step 5: Implementar `services/producto_service.py`**

```python
# backend/app/services/producto_service.py
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Categoria, Producto
from app.schemas.producto import ProductoCreate, ProductoUpdate


def _ensure_categoria(db: Session, id_categoria: int) -> None:
    if db.get(Categoria, id_categoria) is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "La categoría no existe"
        )


def get_or_404(db: Session, id_producto: int) -> Producto:
    obj = db.get(Producto, id_producto)
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return obj


def list_productos(
    db: Session, id_categoria: int | None = None, disponible: bool | None = None
) -> list[Producto]:
    stmt = select(Producto).order_by(Producto.id_producto)
    if id_categoria is not None:
        stmt = stmt.where(Producto.id_categoria == id_categoria)
    if disponible is not None:
        stmt = stmt.where(Producto.disponible == disponible)
    return list(db.execute(stmt).scalars())


def create(db: Session, data: ProductoCreate) -> Producto:
    _ensure_categoria(db, data.id_categoria)
    obj = Producto(
        id_categoria=data.id_categoria,
        nombre_producto=data.nombre_producto,
        descripcion=data.descripcion,
        precio_venta=data.precio_venta,
        disponible=data.disponible,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update(db: Session, id_producto: int, data: ProductoUpdate) -> Producto:
    obj = get_or_404(db, id_producto)
    if data.id_categoria is not None:
        _ensure_categoria(db, data.id_categoria)
    for campo in ("id_categoria", "nombre_producto", "descripcion", "precio_venta", "disponible"):
        valor = getattr(data, campo)
        if valor is not None:
            setattr(obj, campo, valor)
    db.commit()
    db.refresh(obj)
    return obj


def soft_delete(db: Session, id_producto: int) -> Producto:
    obj = get_or_404(db, id_producto)
    obj.disponible = False
    db.commit()
    db.refresh(obj)
    return obj
```

- [ ] **Step 6: Implementar `api/v1/productos.py`**

```python
# backend/app/api/v1/productos.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import Usuario
from app.schemas.producto import ProductoCreate, ProductoOut, ProductoUpdate
from app.services import producto_service

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get("", response_model=list[ProductoOut])
def listar(
    id_categoria: int | None = None,
    disponible: bool | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return producto_service.list_productos(db, id_categoria, disponible)


@router.get("/{id_producto}", response_model=ProductoOut)
def detalle(id_producto: int, db: Session = Depends(get_db), _: Usuario = Depends(deps.get_current_user)):
    return producto_service.get_or_404(db, id_producto)


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED)
def crear(data: ProductoCreate, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return producto_service.create(db, data)


@router.patch("/{id_producto}", response_model=ProductoOut)
def editar(id_producto: int, data: ProductoUpdate, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return producto_service.update(db, id_producto, data)


@router.delete("/{id_producto}", response_model=ProductoOut)
def desactivar(id_producto: int, db: Session = Depends(get_db), _: Usuario = Depends(deps.require_admin)):
    return producto_service.soft_delete(db, id_producto)
```

- [ ] **Step 7: Registrar el router en `api/v1/router.py`**

```python
from app.api.v1 import auth, categorias, mesas, productos, roles, usuarios
# ...
api_router.include_router(productos.router)
```

- [ ] **Step 8: Correr y verificar que pasan**

Run: `docker compose exec -T api pytest tests/test_productos_api.py -v`
Expected: PASS (6 tests).

- [ ] **Step 9: Commit**

```bash
git add backend/app/models/producto.py backend/app/schemas/producto.py backend/app/services/producto_service.py backend/app/api/v1/productos.py backend/app/api/v1/router.py backend/tests/test_productos_api.py
git commit -m "feat(api): CRUD de productos con categoria anidada y soft-delete"
```

---

### Task 4: Seed de catálogo demo

**Files:**
- Modify: `backend/app/db/seed.py`
- Test: `backend/tests/test_seed_catalogo.py`

**Interfaces:**
- Consumes: modelos `Mesa`, `Producto`, `Categoria`.
- Produces: `seed_catalogo(db) -> int` (nº de filas nuevas); integrado en `run()`.

- [ ] **Step 1: Escribir el test que falla**

```python
# backend/tests/test_seed_catalogo.py
from app.db.seed import seed_catalogo
from app.models import Mesa, Producto


def test_seed_catalogo_crea_e_idempotente(db):
    seed_catalogo(db)
    assert db.query(Mesa).count() >= 10
    assert db.query(Producto).count() >= 7
    # idempotente
    creados = seed_catalogo(db)
    assert creados == 0
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `docker compose exec -T api pytest tests/test_seed_catalogo.py -v`
Expected: FAIL (ImportError: cannot import name 'seed_catalogo').

- [ ] **Step 3: Añadir `seed_catalogo` a `seed.py`**

Añadir los imports que falten (`Mesa`, `Producto` ya se importan si no, añadirlos) y la función:

```python
# backend/app/db/seed.py  (asegurar en el import de modelos: Mesa, Producto, Categoria)
```

```python
# backend/app/db/seed.py  (añadir función)
MESAS_DEMO = [
    {"numero_mesa": n, "capacidad": cap, "ubicacion": ubic, "estado": "Disponible"}
    for n, cap, ubic in [
        (1, 2, "Interior"), (2, 2, "Interior"), (3, 4, "Interior"),
        (4, 4, "Interior"), (5, 4, "Terraza"), (6, 6, "Terraza"),
        (7, 6, "Terraza"), (8, 8, "Salón"), (9, 4, "Salón"), (10, 2, "Barra"),
    ]
]

PRODUCTOS_DEMO = [
    ("Bebidas", "Café Americano", "Café negro", 30.0),
    ("Bebidas", "Capuchino", "Con espuma de leche", 42.0),
    ("Bebidas", "Jugo de Naranja", "Natural", 38.0),
    ("Comidas", "Sándwich de Jamón", "Con queso", 65.0),
    ("Comidas", "Ensalada César", "Con pollo", 85.0),
    ("Postres", "Pastel de Chocolate", "Rebanada", 55.0),
    ("Postres", "Flan Napolitano", "Casero", 45.0),
]


def seed_catalogo(db) -> int:
    """Siembra mesas y productos demo. Idempotente."""
    total = 0
    for m in MESAS_DEMO:
        existe = db.query(Mesa).filter(Mesa.numero_mesa == m["numero_mesa"]).first()
        if not existe:
            db.add(Mesa(**m))
            total += 1
    for cat_nombre, nombre, desc, precio in PRODUCTOS_DEMO:
        existe = db.query(Producto).filter(Producto.nombre_producto == nombre).first()
        if existe:
            continue
        cat = db.query(Categoria).filter(Categoria.nombre_categoria == cat_nombre).one()
        db.add(
            Producto(
                id_categoria=cat.id_categoria,
                nombre_producto=nombre,
                descripcion=desc,
                precio_venta=precio,
                disponible=True,
            )
        )
        total += 1
    db.flush()
    return total
```

En `run()`, tras `total += seed_admin(db)` y antes de `db.commit()`, añadir:

```python
        total += seed_catalogo(db)
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `docker compose exec -T api pytest tests/test_seed_catalogo.py -v`
Expected: PASS.

- [ ] **Step 5: Sembrar la BD dev y verificar por HTTP**

```bash
docker compose exec -T api python -m app.db.seed
```
Luego, con un token admin:
```bash
ACCESS=$(curl -s -X POST http://localhost:8000/api/v1/auth/login -d "username=admin@cafeteria.com&password=cambiar_en_local" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -s "http://localhost:8000/api/v1/mesas" -H "Authorization: Bearer $ACCESS" | python3 -c "import sys,json;print('mesas:',len(json.load(sys.stdin)))"
curl -s "http://localhost:8000/api/v1/productos?disponible=true" -H "Authorization: Bearer $ACCESS" | python3 -c "import sys,json;print('productos:',len(json.load(sys.stdin)))"
```
Expected: mesas ≥ 10, productos ≥ 7.

- [ ] **Step 6: Correr toda la suite**

Run: `docker compose exec -T api pytest -q`
Expected: PASS (todas: las 35 previas + las de catálogo).

- [ ] **Step 7: Commit**

```bash
git add backend/app/db/seed.py backend/tests/test_seed_catalogo.py
git commit -m "feat(db): seed de mesas y productos demo"
```

---

## Cierre

- [ ] Push: `git push -u origin feature/api-catalogo`
- [ ] Abrir PR hacia `main`.

## Self-Review (cobertura del spec)

- Mesas CRUD + estado validado + delete FK-safe → Task 2. ✅
- Categorías CRUD + delete FK-safe (409 con productos) → Task 1. ✅
- Productos CRUD + categoría anidada + soft-delete + filtros menú → Task 3. ✅
- Autorización GET-auth / write-admin (401/403) → Tasks 1,2,3. ✅
- Unicidad (409), validaciones (422 estado/precio/capacidad/categoría), 404 → Tasks 1,2,3. ✅
- `ProductoOut` con categoría → Task 3. ✅
- Seed demo mesas + productos → Task 4. ✅
- Fuera de alcance (pedidos, recetas, web CRUD): ausente. ✅
