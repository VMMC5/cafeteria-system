# Diseño — App móvil Mesero: toma de pedido (feature/mobile-mesero)

**Fecha:** 2026-07-05
**Sprint:** 2 (slice 3 de 3: móvil Mesero)
**Rama:** `feature/mobile-mesero`

## Objetivo

Que un Mesero, tras iniciar sesión, aterrice directo en su módulo y complete el flujo
de toma de pedido: elegir mesa → navegar el menú por categoría → armar el carrito con
total en vivo → confirmar el pedido (consumiendo las APIs de catálogo y pedidos de los
slices 1 y 2). Cierra el Sprint 2.

Cubre RF-M04 (auto-navegación), RF-M05..M17.

## Decisiones tomadas (brainstorming)

1. **Auto-navegación por rol:** si el rol tiene 1 módulo → home directa (Mesero →
   `/mesero/mesas`); si tiene varios (Admin) → `/seleccion-modulo`.
2. **Solo mesas Disponible** inician un pedido; Ocupada/Reservada se ven pero deshabilitadas.
3. **Carrito en memoria** (zustand), con total en vivo; se limpia al confirmar o salir.
4. **Fetch simple** (estado local + `useFocusEffect`), sin react-query.
5. **Testing:** jest sobre la lógica del carrito; pantallas por verificación manual.

## Navegación (expo-router)

```
src/app/
├── index.tsx            # (mod) auto-navegación por rol tras bootstrap
├── seleccion-modulo.tsx # (sin cambios) para Admin
├── modulo/[key].tsx     # placeholder Caja/Cocina (sin cambios)
└── mesero/
    ├── mesas.tsx        # /mesero/mesas — home del Mesero (con "Salir")
    ├── menu.tsx         # /mesero/menu
    └── carrito.tsx      # /mesero/carrito
```

- `src/lib/modules.ts`: `MESERO.ruta` pasa de `/modulo/mesero` a `/mesero/mesas`.
- `_layout.tsx`: registrar las nuevas pantallas en el Stack.
- `index.tsx`: tras `bootstrap`, si `status==="auth"`: `modulos = modulesForRole(rol)`;
  si `modulos.length === 1` → `Redirect` a `modulos[0].ruta`; si no → `/seleccion-modulo`.

## Pantallas

### `mesero/mesas.tsx` (RF-M05..M08)
- Carga `getMesas(access)` al enfocar (`useFocusEffect`) para reflejar cambios de estado.
- Grid de tarjetas: número, capacidad, badge de estado (Disponible/Ocupada/Reservada).
- **Solo Disponible** es tocable → `cart.setMesa(id, numero)`, `cart.clear()` (items),
  navegar a `/mesero/menu`. Las demás se muestran atenuadas.
- Header con "Salir" → `auth.logout()` + `router.replace("/login")`.
- Estados: cargando (spinner), error de red (mensaje + reintentar), vacío.

### `mesero/menu.tsx` (RF-M09..M13)
- Carga `getCategorias(access)` y `getProductos(access, {disponible:true})`.
- Productos agrupados por categoría (secciones). Cada producto: nombre, precio, y
  controles **+ / −** que reflejan la cantidad en el carrito (`cart.incItem/decItem`).
- Barra inferior fija: "Ver pedido (N ítems) — $<total en vivo>" → `/mesero/carrito`
  (deshabilitada si el carrito está vacío).

### `mesero/carrito.tsx` (RF-M14..M17)
- Lista las líneas del carrito: nombre, cantidad con **+/−**, subtotal (cantidad × precio).
- Campo de **observaciones** general del pedido (`cart.setObservaciones`).
- Total. Botón **Confirmar pedido** (deshabilitado si vacío):
  - `crearPedido(access, cart.toPayload())`.
  - Éxito → `cart.clear()`, aviso de éxito, `router.replace("/mesero/mesas")`.
  - Error 409 (mesa ocupada) → mensaje; otro error → "no se pudo enviar el pedido".

## Estado del carrito — `src/store/cart.ts` (zustand)

```ts
type ProductoCarrito = { id_producto: number; nombre_producto: string; precio_venta: number };
type CartItem = { producto: ProductoCarrito; cantidad: number; observaciones?: string | null };

state: {
  id_mesa: number | null;
  mesa_numero: number | null;
  items: CartItem[];
  observaciones: string;
}
acciones: setMesa(id, numero), addItem(producto), incItem(id_producto),
          decItem(id_producto) /* a 0 elimina */, removeItem(id_producto),
          setObservaciones(txt), clear()
```

Helpers puros (testeables, exportados):
- `cartTotal(items): number` → Σ `cantidad × precio_venta`.
- `cartCount(items): number` → Σ `cantidad`.
- `toPayload(state)` → `{ id_mesa, observaciones, items: [{id_producto, cantidad, observaciones}] }`.

`incItem` sobre un producto no presente lo agrega con cantidad 1 (equivale a `addItem`).

## API client — extender `src/api/client.ts`

Tipos nuevos: `Mesa`, `Categoria`, `Producto`, `Pedido` (mínimos para la UI).
Funciones (token explícito, como `getMe`):
- `getMesas(access, estado?) -> Mesa[]` → `GET /mesas`.
- `getCategorias(access) -> Categoria[]` → `GET /categorias`.
- `getProductos(access, opts?) -> Producto[]` → `GET /productos` con `id_categoria`/`disponible`.
- `crearPedido(access, payload) -> Pedido` → `POST /pedidos`.

El token se obtiene en las pantallas con `useAuth((s) => s.accessToken)`.

## Manejo de errores

| Situación | UI |
|---|---|
| Sin red al cargar mesas/menú | Mensaje + botón "Reintentar" |
| Carrito vacío | Botón Confirmar / "Ver pedido" deshabilitado |
| 409 al confirmar (mesa ocupada) | Mensaje; al volver a mesas se ve Ocupada |
| Otro error al confirmar | "No se pudo enviar el pedido" |
| Token expirado (401) | Lo maneja el flujo de auth existente |

## Testing (jest, lógica pura)

`src/store/cart.test.ts`:
- `addItem` agrega; `incItem` repetido suma; `decItem` baja y a 0 elimina; `removeItem` quita.
- `cartTotal` y `cartCount` correctos con varias líneas.
- `toPayload` produce `{id_mesa, observaciones, items:[{id_producto, cantidad, observaciones}]}`.
- `clear` vacía y resetea la mesa.

Pantallas: verificación manual en Expo (login como `mesero@cafeteria.com` → mesas →
menú → carrito → confirmar → ver la mesa Ocupada).

## Fuera de alcance (YAGNI)

"Mis pedidos" y estado en vivo (RF-M18..M26, Sprint 3), módulos Caja/Cocina, edición de
un pedido ya enviado, pagos (Sprint 4), notificaciones, persistencia del carrito entre
reinicios.
