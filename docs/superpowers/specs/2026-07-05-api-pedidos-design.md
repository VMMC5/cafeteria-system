# Diseño — API de Pedidos: crear y consultar pedidos (feature/api-pedidos)

**Fecha:** 2026-07-05
**Sprint:** 2 (slice 2 de 3: pedidos)
**Rama:** `feature/api-pedidos`

## Objetivo

Permitir crear un pedido con sus líneas (producto, cantidad, observaciones) y
consultarlo, con cálculo de totales y transición de estado de la mesa. Segundo slice
del Sprint 2; el tercero son las pantallas del Mesero que consumen esta API.

Cubre el backend de RF-M10..M17.

## Decisiones tomadas (brainstorming)

1. **Mesa:** crear pedido requiere mesa **Disponible** → 409 si no; al crear pasa a **Ocupada**.
2. **Producto no disponible o inexistente en una línea → 422** (se rechaza todo el pedido).
3. **Precio congelado:** el server toma `precio_venta` actual del producto; el cliente no manda precios.
4. **Total derivado:** `pedidos` no tiene columna total; se calcula como Σ subtotales (propiedad del modelo).

## Endpoints (`/api/v1`)

Convención: todos requieren `deps.get_current_user` (autenticado).

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/pedidos` | Crear pedido; el usuario actual es el mesero |
| GET | `/pedidos` (`?id_estado=` `&mias=true`) | Listar; `mias` filtra por el usuario actual |
| GET | `/pedidos/{id}` | Detalle con líneas y total |

## Crear pedido — lógica (`pedido_service.crear`)

Entrada (`PedidoCreate`):
```json
{
  "id_mesa": 3,
  "observaciones": "Sin cebolla",
  "items": [
    {"id_producto": 5, "cantidad": 2, "observaciones": null}
  ]
}
```

Pasos y reglas:
1. La mesa debe existir (404 si no) y estar **Disponible** (409 si `Ocupada`/`Reservada`).
2. `items` no vacío (≥ 1) y cada `cantidad` ≥ 1 (422 vía schema).
3. Cada `id_producto` debe existir y tener `disponible=true`; si no, **422** y no se crea nada.
4. Por cada ítem, el server lee `producto.precio_venta` actual y lo guarda en
   `detalle_pedido.precio_unitario` (histórico). `subtotal` lo calcula la BD
   (columna generada `cantidad * precio_unitario`).
5. Se crea el `Pedido` con `id_estado` = **Pendiente**, `id_usuario` = usuario actual,
   `observaciones` del encabezado, y sus `DetallePedido`.
6. La mesa pasa a **Ocupada**.
7. Todo en una transacción; se devuelve el pedido creado con total.

Crear el pedido **confirma y lo envía** (no hay estado borrador; el carrito vive en el
cliente móvil — slice 3). Cubre RF-M17.

## Cálculo de totales

`total = Σ (detalle.subtotal)`. Se expone como propiedad Python del modelo
`Pedido.total`, leída por `PedidoOut` (from_attributes). Cubre RF-M11/M13/M15.

## Relaciones ORM añadidas (sin migración)

- `Pedido.mesa = relationship("Mesa")`
- `Pedido.estado = relationship("EstadoPedido")`
- `Pedido.detalle = relationship("DetallePedido")`
- `Pedido.total` → `@property` que suma `d.subtotal`
- `DetallePedido.producto = relationship("Producto")`

## Schemas

- `PedidoItemCreate`: `id_producto: int`, `cantidad: int (ge=1)`, `observaciones: str | None`.
- `PedidoCreate`: `id_mesa: int`, `observaciones: str | None`, `items: list[PedidoItemCreate]` (min_length=1).
- `DetalleOut`: `id_detalle`, `id_producto`, `producto: ProductoResumen` (`{id_producto, nombre_producto}`),
  `cantidad`, `precio_unitario`, `subtotal`, `observaciones`.
- `EstadoResumen`: `{id_estado, nombre_estado}`. `MesaResumen`: `{id_mesa, numero_mesa}`.
- `PedidoOut`: `id_pedido`, `id_mesa`, `mesa: MesaResumen`, `id_estado`,
  `estado: EstadoResumen`, `id_usuario`, `fecha_pedido`, `observaciones`,
  `detalle: list[DetalleOut]`, `total: Decimal`.

## Manejo de errores

| Situación | Código |
|---|---|
| Sin token | 401 |
| Mesa inexistente | 404 |
| Mesa no Disponible | 409 |
| Producto inexistente o `disponible=false` en una línea | 422 |
| `items` vacío o `cantidad` < 1 | 422 |
| Pedido inexistente (GET/{id}) | 404 |

## Componentes

```
backend/app/
├── models/pedido.py       # + relaciones y property total
├── schemas/pedido.py      # PedidoCreate, PedidoItemCreate, PedidoOut, DetalleOut, resúmenes
├── services/pedido_service.py  # crear, get_or_404, list_pedidos
└── api/v1/pedidos.py      # router (registrado en router.py)
```

## Testing (`pytest` en el contenedor)

Reutiliza `client`, `admin_headers`, `mesero_headers`. Crea mesa/producto vía los
endpoints del slice 1. Casos:
- Crear pedido OK → 201; mesa pasa a `Ocupada`; `total` = suma correcta; `precio_unitario`
  = precio del producto al crear (aunque luego cambie el precio del producto).
- Crear en mesa ya `Ocupada` → 409.
- Ítem con producto no disponible → 422; sin ítems → 422; cantidad 0 → 422.
- `GET /pedidos?mias=true` devuelve solo los del usuario.
- `GET /pedidos/{id}` trae las líneas con `producto.nombre_producto` y el total.

## Fuera de alcance (YAGNI)

Transiciones de estado Pendiente→En preparación→Listo→Entregado (Sprint 3, cocina),
cancelaciones, cobro/venta (Sprint 4), descuento de inventario por receta (Sprint 5),
pantallas del Mesero (slice 3), edición/borrado de pedidos.
