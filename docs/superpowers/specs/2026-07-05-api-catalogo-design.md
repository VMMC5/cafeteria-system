# Diseño — API de Catálogo: mesas, categorías, productos (feature/api-catalogo)

**Fecha:** 2026-07-05
**Sprint:** 2 (slice 1 de 3: catálogo)
**Rama:** `feature/api-catalogo`

## Objetivo

Exponer en la API los endpoints de catálogo que consumirá el módulo Mesero
(mesas con estado, menú por categoría) y que un Administrador usará para gestionar
mesas, categorías y productos. Primer slice del Sprint 2; le siguen la API de
pedidos (slice 2) y las pantallas del Mesero (slice 3).

Cubre el backend de RF-M05..M09 y el CRUD de catálogo.

## Decisiones tomadas (brainstorming)

1. **Descomposición del Sprint 2:** 3 slices — API catálogo → API pedidos → móvil Mesero.
2. **Autorización:** GET para cualquier usuario autenticado; POST/PATCH/DELETE solo Administrador.
3. **Borrado FK-safe:** productos → soft-delete (`disponible=false`); categorías y mesas →
   borrado real solo si no están referenciadas, si no 409.
4. **Seed demo:** ~8-10 mesas + productos de ejemplo por categoría.

## Endpoints (bajo `/api/v1`)

Convención: **GET = `get_current_user`**, **POST/PATCH/DELETE = `require_admin`**.

### Mesas
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/mesas` (`?estado=`) | auth | Listar mesas con su estado |
| GET | `/mesas/{id}` | auth | Detalle |
| POST | `/mesas` | admin | Crear (numero_mesa único) |
| PATCH | `/mesas/{id}` | admin | Editar (incl. estado) |
| DELETE | `/mesas/{id}` | admin | 409 si tiene pedidos; si no, borra |

### Categorías
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/categorias` | auth | Listar |
| GET | `/categorias/{id}` | auth | Detalle |
| POST | `/categorias` | admin | Crear (nombre único) |
| PATCH | `/categorias/{id}` | admin | Editar |
| DELETE | `/categorias/{id}` | admin | 409 si tiene productos; si no, borra |

### Productos
| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| GET | `/productos` (`?id_categoria=` `&disponible=`) | auth | Listar (menú: `disponible=true`) |
| GET | `/productos/{id}` | auth | Detalle |
| POST | `/productos` | admin | Crear (id_categoria existe, precio ≥ 0) |
| PATCH | `/productos/{id}` | admin | Editar |
| DELETE | `/productos/{id}` | admin | **Soft-delete** (`disponible=false`) |

## Reglas y validaciones

- **Estado de mesa** restringido a `Disponible` / `Ocupada` / `Reservada` (422 si otro).
  La transición automática a "Ocupada" al crear un pedido es del **slice 2**; aquí el
  estado se gestiona manualmente vía PATCH.
- **`ProductoOut` incluye la categoría anidada** (`categoria: CategoriaOut`), vía
  relación ORM `Producto.categoria` (sin migración), para que el móvil agrupe el menú.
- **Unicidad:** `numero_mesa`, `nombre_categoria` → 409 si duplicado.
- **Precio:** `precio_venta` ≥ 0 (422). **Capacidad:** ≥ 1 (422).
- **FK inexistente:** producto con `id_categoria` que no existe → 422.
- **404:** id inexistente en cualquier detalle/mutación.

## Componentes (siguiendo el patrón de `usuarios`)

```
backend/app/
├── schemas/
│   ├── mesa.py        # MesaCreate, MesaUpdate, MesaOut
│   ├── categoria.py   # CategoriaCreate, CategoriaUpdate, CategoriaOut
│   └── producto.py    # ProductoCreate, ProductoUpdate, ProductoOut (categoria anidada)
├── services/
│   ├── mesa_service.py       # CRUD + unicidad + delete FK-safe
│   ├── categoria_service.py  # CRUD + unicidad + delete FK-safe
│   └── producto_service.py   # CRUD + validación categoría/precio + soft-delete
├── api/v1/
│   ├── mesas.py       # router
│   ├── categorias.py  # router
│   └── productos.py   # router (registrados en router.py)
└── models/producto.py # + relationship Producto.categoria
```

`CategoriaOut` sustituye/duplica el patrón `RolOut`. Los routers son finos y delegan
en los services; los services contienen la lógica de negocio (unicidad, FK, soft-delete).

## Manejo de errores

| Situación | Código |
|---|---|
| GET sin token | 401 |
| Mutación sin rol admin | 403 |
| numero_mesa / nombre_categoria duplicado | 409 |
| Borrar mesa con pedidos / categoría con productos | 409 |
| Estado de mesa inválido, precio<0, capacidad<1, id_categoria inexistente | 422 |
| id inexistente | 404 |

## Seed de ejemplo (extiende `db/seed.py`, idempotente)

- **Mesas:** números 1..10, capacidades entre 2 y 8, `ubicacion` variada, estado
  `Disponible`. Idempotente por `numero_mesa`.
- **Productos demo** (usa las categorías ya sembradas Bebidas/Comidas/Postres):
  - Bebidas: Café Americano, Capuchino, Jugo de Naranja.
  - Comidas: Sándwich de Jamón, Ensalada César.
  - Postres: Pastel de Chocolate, Flan Napolitano.
  Con `precio_venta` y `disponible=true`. Idempotente por `nombre_producto`.

## Testing (`pytest` en el contenedor)

Reutiliza `client`, `admin_headers`, `mesero_headers`. Por entidad:
- Listar (auth) y crear/editar (admin) OK.
- Autorización: GET sin token → 401; POST con `mesero_headers` → 403.
- Unicidad → 409; validaciones (estado/precio/capacidad/categoría) → 422; 404.
- Borrado FK-safe: mesa con pedido / categoría con producto → 409.
- Producto DELETE → `disponible=false` y desaparece del menú (`?disponible=true`).
- `GET /productos/{id}` trae `categoria.nombre_categoria`.

## Fuera de alcance (YAGNI)

Creación de pedidos y transición de estado de mesa (slice 2), recetas/inventario
`producto_insumo` (Sprint 5), CRUD de catálogo en la web admin (futuro), imágenes de
productos, paginación (los catálogos son pequeños).
