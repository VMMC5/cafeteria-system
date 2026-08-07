# Recetas en el módulo Cocina (móvil) — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El Cocinero (o Administrador) puede ver y editar desde la app la receta de cada producto — qué insumos lleva y en qué cantidad — cerrando el pendiente "Recetas solo por Swagger".

**Architecture:** Un solo endpoint nuevo en la API (`PATCH` de una línea de receta) más cuatro funciones en el api-client del móvil, un módulo de lógica pura (`src/lib/recetas.ts`) con toda la validación testeable, y dos pantallas nuevas en el módulo Cocina (lista de productos → detalle de receta con edición inline). Las pantallas quedan como capa delgada: toda regla de negocio vive en `lib/recetas.ts`, que es lo que se testea.

**Tech Stack:** Backend FastAPI + SQLAlchemy + pytest · Móvil React Native + Expo SDK 57 (expo-router) + TypeScript + Jest.

**Spec:** `docs/superpowers/specs/2026-08-06-recetas-cocina-movil-design.md`

## Global Constraints

- **Expo SDK 57:** antes de escribir código de pantallas, consultar los docs versionados en https://docs.expo.dev/versions/v57.0.0/ (regla de `mobile/AGENTS.md`). Verificado ya para este plan: `useLocalSearchParams`, `router.push` y `router.replace` siguen vigentes en SDK 57; **prohibido importar de `@react-navigation/*`** en código de aplicación (SDK 56+), usar los entry points de `expo-router`.
- **Decimal como string:** la API serializa `Decimal` como string en JSON. Los stubs de test del cliente deben usar **strings** (`"0.25"`), no floats. La coerción a `number` se hace en el borde vía `coerce.ts`.
- **Roles:** la API ya restringe recetas a `{"Cocinero", "Administrador"}` (403 si no). Las pantallas no implementan lógica de permisos propia.
- **Rutas del móvil:** `router.push("/ruta" as any)` — el cast `as any` es el patrón vigente en este repo para rutas tipadas de expo-router.
- **Estilos:** reusar la paleta de las pantallas de Cocina (`#f4f5f7` fondo, `#2b6cb0` primario, `#2d3748` texto, `#c53030` error, `#718096` muted).
- **Commits:** en español, formato `tipo(scope): descripción` (p. ej. `feat(mobile):`, `test(api):`).
- **Rama:** todo el trabajo va en `feat/mobile-recetas` (worktree aislado bajo `.claude/worktrees/`, creado al arrancar la ejecución). `main` no se toca hasta el merge del PR.
- **Tests del móvil en worktree:** correr `npx jest` desde el `mobile/` del worktree. Para el backend, `docker compose exec api pytest` corre contra el checkout **principal**, así que los tests de Task 1 se verifican levantando el stack desde el worktree o corriendo pytest en un venv local del worktree.

## Estructura de archivos

| Archivo | Responsabilidad | Acción |
|---|---|---|
| `backend/app/schemas/receta.py` | Schema `RecetaLineaUpdate` | Modificar |
| `backend/app/services/receta_service.py` | `actualizar_linea()` | Modificar |
| `backend/app/api/v1/recetas.py` | Ruta `PATCH` | Modificar |
| `backend/tests/test_recetas_api.py` | Tests del PATCH | Modificar |
| `mobile/src/api/coerce.ts` | Añadir `cantidad_requerida` a `DECIMAL_FIELDS` | Modificar |
| `mobile/src/api/client.ts` | Tipo `RecetaLinea` + 4 funciones | Modificar |
| `mobile/src/lib/recetas.ts` | Lógica pura (validación, filtro, disponibles) | Crear |
| `mobile/src/lib/recetas.test.ts` | Tests de la lógica pura | Crear |
| `mobile/src/app/cocina/recetas.tsx` | Pantalla lista de productos | Crear |
| `mobile/src/app/cocina/receta-detalle.tsx` | Pantalla detalle con edición inline | Crear |
| `mobile/src/app/cocina/index.tsx` | Enlace "Recetas" en el menú | Modificar |
| `progress.md` | Bitácora | Modificar |

**Orden de dependencias:** Task 1 (backend) → Task 2 (client) → Task 3 (lib) → Task 4 (lista) → Task 5 (detalle) → Task 6 (verificación + docs). Tasks 2 y 3 son independientes entre sí; 4 y 5 consumen ambas.

**Comandos de test:**
- Backend: `docker compose exec api pytest tests/test_recetas_api.py -v`
- Móvil: `cd mobile && npx jest <ruta>`

---

### Task 1: Backend — `PATCH` de una línea de receta

**Files:**
- Modify: `backend/app/schemas/receta.py`
- Modify: `backend/app/services/receta_service.py`
- Modify: `backend/app/api/v1/recetas.py`
- Test: `backend/tests/test_recetas_api.py`

**Interfaces:**
- Consumes: nada (primera task).
- Produces: endpoint `PATCH /api/v1/productos/{id_producto}/receta/{id_producto_insumo}` con body `{"cantidad_requerida": <número > 0>}` que responde `200` con el objeto `RecetaLineaOut` (`{id_producto_insumo, id_insumo, insumo: {id_insumo, nombre_insumo, unidad: {abreviatura}}, cantidad_requerida}`). Lo consume Task 2.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir al final de la sección de recetas de `backend/tests/test_recetas_api.py` (justo después de `test_receta_rol_mesero_403`, antes de `_mesa_id`). Los helpers `_producto_id` e `_insumo_id` ya existen arriba en el archivo:

```python
def _linea(client, db, admin_headers, cocinero_headers, prod, ins, cant=0.02):
    pid = _producto_id(client, db, admin_headers, nombre=prod)
    iid = _insumo_id(client, db, cocinero_headers, nombre=ins)
    linea = client.post(
        f"/api/v1/productos/{pid}/receta",
        headers=cocinero_headers,
        json={"id_insumo": iid, "cantidad_requerida": cant},
    ).json()
    return pid, linea["id_producto_insumo"]


def test_patch_linea_ok(client, db, admin_headers, cocinero_headers):
    pid, lid = _linea(client, db, admin_headers, cocinero_headers, "Mocaccino", "Cacao2")
    r = client.patch(
        f"/api/v1/productos/{pid}/receta/{lid}",
        headers=cocinero_headers,
        json={"cantidad_requerida": 0.5},
    )
    assert r.status_code == 200
    assert float(r.json()["cantidad_requerida"]) == 0.5
    lista = client.get(
        f"/api/v1/productos/{pid}/receta", headers=cocinero_headers
    ).json()
    assert float(lista[0]["cantidad_requerida"]) == 0.5


def test_patch_linea_inexistente_404(client, db, admin_headers, cocinero_headers):
    pid = _producto_id(client, db, admin_headers, nombre="Ristretto")
    r = client.patch(
        f"/api/v1/productos/{pid}/receta/999999",
        headers=cocinero_headers,
        json={"cantidad_requerida": 1.0},
    )
    assert r.status_code == 404


def test_patch_linea_de_otro_producto_404(client, db, admin_headers, cocinero_headers):
    _, lid = _linea(client, db, admin_headers, cocinero_headers, "Macchiato", "Vainilla")
    otro = _producto_id(client, db, admin_headers, nombre="Affogato")
    r = client.patch(
        f"/api/v1/productos/{otro}/receta/{lid}",
        headers=cocinero_headers,
        json={"cantidad_requerida": 1.0},
    )
    assert r.status_code == 404


def test_patch_cantidad_cero_422(client, db, admin_headers, cocinero_headers):
    pid, lid = _linea(client, db, admin_headers, cocinero_headers, "Lungo", "Agua2")
    r = client.patch(
        f"/api/v1/productos/{pid}/receta/{lid}",
        headers=cocinero_headers,
        json={"cantidad_requerida": 0},
    )
    assert r.status_code == 422


def test_patch_rol_mesero_403(client, db, admin_headers, cocinero_headers, mesero_headers):
    pid, lid = _linea(client, db, admin_headers, cocinero_headers, "Irlandés", "Crema")
    r = client.patch(
        f"/api/v1/productos/{pid}/receta/{lid}",
        headers=mesero_headers,
        json={"cantidad_requerida": 1.0},
    )
    assert r.status_code == 403
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `docker compose exec api pytest tests/test_recetas_api.py -k patch -v`
Expected: FAIL — los 5 tests dan `405 Method Not Allowed` (la ruta PATCH no existe todavía).

- [ ] **Step 3: Añadir el schema**

En `backend/app/schemas/receta.py`, después de `class RecetaLineaCreate`:

```python
class RecetaLineaUpdate(BaseModel):
    cantidad_requerida: Decimal = Field(gt=0)
```

- [ ] **Step 4: Añadir el servicio**

En `backend/app/services/receta_service.py`, importar el schema nuevo en la línea de import existente:

```python
from app.schemas.receta import RecetaLineaCreate, RecetaLineaUpdate
```

Y añadir la función justo después de `agregar_linea` (antes de `eliminar_linea`). La validación de pertenencia es la misma que usa `eliminar_linea`:

```python
def actualizar_linea(
    db: Session,
    id_producto: int,
    id_producto_insumo: int,
    data: RecetaLineaUpdate,
    usuario,
) -> ProductoInsumo:
    _check_rol(usuario)
    linea = db.get(ProductoInsumo, id_producto_insumo)
    if linea is None or linea.id_producto != id_producto:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Línea de receta no encontrada"
        )
    linea.cantidad_requerida = data.cantidad_requerida
    db.commit()
    db.refresh(linea)
    return linea
```

- [ ] **Step 5: Añadir la ruta**

En `backend/app/api/v1/recetas.py`, actualizar el import de schemas:

```python
from app.schemas.receta import RecetaLineaCreate, RecetaLineaOut, RecetaLineaUpdate
```

Y añadir la ruta entre `agregar` y `eliminar`:

```python
@router.patch(
    "/{id_producto}/receta/{id_producto_insumo}",
    response_model=RecetaLineaOut,
)
def actualizar(
    id_producto: int,
    id_producto_insumo: int,
    data: RecetaLineaUpdate,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    return receta_service.actualizar_linea(
        db, id_producto, id_producto_insumo, data, current
    )
```

- [ ] **Step 6: Correr los tests y verificar que pasan**

Run: `docker compose exec api pytest tests/test_recetas_api.py -v`
Expected: PASS — todos los tests del archivo (los previos + los 5 nuevos).

- [ ] **Step 7: Correr la suite completa del backend (no regresión)**

Run: `docker compose exec api pytest`
Expected: PASS — 201 tests previos + 5 nuevos = 206.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/receta.py backend/app/services/receta_service.py \
        backend/app/api/v1/recetas.py backend/tests/test_recetas_api.py
git commit -m "feat(api): PATCH de línea de receta para editar la cantidad requerida"
```

---

### Task 2: API-client móvil — tipos y funciones de receta

**Files:**
- Modify: `mobile/src/api/coerce.ts`
- Modify: `mobile/src/api/client.ts`
- Test: `mobile/src/api/coerce.test.ts`, `mobile/src/api/client.test.ts`

**Interfaces:**
- Consumes: el endpoint PATCH de Task 1.
- Produces (lo usan Tasks 4 y 5):
  - `type RecetaLinea = { id_producto_insumo: number; id_insumo: number; insumo: { id_insumo: number; nombre_insumo: string; unidad: { abreviatura: string } }; cantidad_requerida: number }`
  - `getReceta(access: string, idProducto: number): Promise<RecetaLinea[]>`
  - `addRecetaLinea(access: string, idProducto: number, data: { id_insumo: number; cantidad_requerida: number }): Promise<RecetaLinea>`
  - `patchRecetaLinea(access: string, idProducto: number, idProductoInsumo: number, cantidad: number): Promise<RecetaLinea>`
  - `deleteRecetaLinea(access: string, idProducto: number, idProductoInsumo: number): Promise<void>`

- [ ] **Step 1: Escribir el test de coerción que falla**

`cantidad_requerida` NO está en `DECIMAL_FIELDS` (el set tiene `cantidad`, que es otra clave), así que hoy llegaría como string. Añadir a `mobile/src/api/coerce.test.ts`:

```typescript
test("coacciona cantidad_requerida de las líneas de receta", () => {
  const receta = [
    {
      id_producto_insumo: 1,
      id_insumo: 7,
      insumo: { id_insumo: 7, nombre_insumo: "Leche", unidad: { abreviatura: "L" } },
      cantidad_requerida: "0.250",
    },
  ];
  const out = coerceDecimals(receta) as any[];
  expect(out[0].cantidad_requerida).toBe(0.25);
  expect(typeof out[0].cantidad_requerida).toBe("number");
});
```

- [ ] **Step 2: Correr el test y verificar que falla**

Run: `cd mobile && npx jest src/api/coerce.test.ts`
Expected: FAIL — `Expected: 0.25, Received: "0.250"`.

- [ ] **Step 3: Añadir el campo al set de coerción**

En `mobile/src/api/coerce.ts`, dentro de `DECIMAL_FIELDS`, añadir después de `"cantidad"`:

```typescript
  "cantidad_requerida",
```

- [ ] **Step 4: Correr el test y verificar que pasa**

Run: `cd mobile && npx jest src/api/coerce.test.ts`
Expected: PASS.

- [ ] **Step 5: Escribir los tests del client que fallan**

Añadir al final de `mobile/src/api/client.test.ts`. Ese archivo importa `* as client from "./client"` y mockea con `jest.spyOn(client.http, "<verbo>")` — **no** hay variables `mockGet`/`mockPost`; usar exactamente este patrón. No hacen falta imports nuevos (todo se accede vía `client.*`). Los stubs usan **strings** para el Decimal, como llega de la API:

```typescript
const LINEA_STUB = {
  id_producto_insumo: 3,
  id_insumo: 7,
  insumo: { id_insumo: 7, nombre_insumo: "Leche entera", unidad: { abreviatura: "L" } },
  cantidad_requerida: "0.25",
};

test("getReceta pega a la receta del producto con el Bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [LINEA_STUB] } as any);
  const out = await client.getReceta("tok", 12);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/productos/12/receta");
  expect(config.headers.Authorization).toBe("Bearer tok");
  expect(out[0].insumo.nombre_insumo).toBe("Leche entera");
});

test("addRecetaLinea postea insumo y cantidad a la receta del producto", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: LINEA_STUB } as any);
  await client.addRecetaLinea("tok", 12, { id_insumo: 7, cantidad_requerida: 0.25 });
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/productos/12/receta");
  expect(body).toEqual({ id_insumo: 7, cantidad_requerida: 0.25 });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("patchRecetaLinea usa el id de línea y manda solo la cantidad", async () => {
  const spy = jest
    .spyOn(client.http, "patch")
    .mockResolvedValue({ data: LINEA_STUB } as any);
  await client.patchRecetaLinea("tok", 12, 3, 0.5);
  const [url, body] = spy.mock.calls[0] as any[];
  expect(url).toBe("/productos/12/receta/3");
  expect(body).toEqual({ cantidad_requerida: 0.5 });
});

test("deleteRecetaLinea usa el id de línea", async () => {
  const spy = jest
    .spyOn(client.http, "delete")
    .mockResolvedValue({ status: 204 } as any);
  await client.deleteRecetaLinea("tok", 12, 3);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/productos/12/receta/3");
  expect(config.headers.Authorization).toBe("Bearer tok");
});
```

- [ ] **Step 6: Correr los tests y verificar que fallan**

Run: `cd mobile && npx jest src/api/client.test.ts`
Expected: FAIL — `getReceta is not a function` (o error de import TS).

- [ ] **Step 7: Implementar tipo y funciones**

En `mobile/src/api/client.ts`, añadir el tipo junto a los otros tipos de insumo (cerca de la línea 161) y las funciones al final del archivo, siguiendo el patrón de `getInsumos`/`crearCompra`:

```typescript
export type RecetaLinea = {
  id_producto_insumo: number;
  id_insumo: number;
  insumo: {
    id_insumo: number;
    nombre_insumo: string;
    unidad: { abreviatura: string };
  };
  cantidad_requerida: number;
};

export async function getReceta(
  access: string,
  idProducto: number
): Promise<RecetaLinea[]> {
  const { data } = await http.get(`/productos/${idProducto}/receta`, authCfg(access));
  return data;
}

export async function addRecetaLinea(
  access: string,
  idProducto: number,
  data: { id_insumo: number; cantidad_requerida: number }
): Promise<RecetaLinea> {
  const { data: res } = await http.post(
    `/productos/${idProducto}/receta`,
    data,
    authCfg(access)
  );
  return res;
}

export async function patchRecetaLinea(
  access: string,
  idProducto: number,
  idProductoInsumo: number,
  cantidad: number
): Promise<RecetaLinea> {
  const { data } = await http.patch(
    `/productos/${idProducto}/receta/${idProductoInsumo}`,
    { cantidad_requerida: cantidad },
    authCfg(access)
  );
  return data;
}

export async function deleteRecetaLinea(
  access: string,
  idProducto: number,
  idProductoInsumo: number
): Promise<void> {
  await http.delete(
    `/productos/${idProducto}/receta/${idProductoInsumo}`,
    authCfg(access)
  );
}
```

- [ ] **Step 8: Correr los tests y verificar que pasan**

Run: `cd mobile && npx jest src/api`
Expected: PASS — coerce.test.ts y client.test.ts completos.

- [ ] **Step 9: Verificar tipos**

Run: `cd mobile && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 10: Commit**

```bash
git add mobile/src/api/coerce.ts mobile/src/api/coerce.test.ts \
        mobile/src/api/client.ts mobile/src/api/client.test.ts
git commit -m "feat(mobile): funciones de receta en el api-client + coerción de cantidad_requerida"
```

---

### Task 3: Lógica pura de recetas (`lib/recetas.ts`)

**Files:**
- Create: `mobile/src/lib/recetas.ts`
- Test: `mobile/src/lib/recetas.test.ts`

**Interfaces:**
- Consumes: el tipo `RecetaLinea` de Task 2.
- Produces (lo usan Tasks 4 y 5):
  - `cantidadValida(txt: string): boolean`
  - `aCantidad(txt: string): number`
  - `filtrarProductos<T extends { nombre_producto: string }>(productos: T[], query: string): T[]`
  - `insumosDisponibles<T extends { id_insumo: number }>(insumos: T[], receta: { id_insumo: number }[]): T[]`

- [ ] **Step 1: Escribir los tests que fallan**

Crear `mobile/src/lib/recetas.test.ts` (patrón de `inventario.test.ts`):

```typescript
import {
  aCantidad,
  cantidadValida,
  filtrarProductos,
  insumosDisponibles,
} from "./recetas";

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

test("aCantidad normaliza la coma decimal a punto", () => {
  expect(aCantidad("0,25")).toBe(0.25);
  expect(aCantidad("0.25")).toBe(0.25);
  expect(aCantidad("3")).toBe(3);
});

test("filtrarProductos ignora mayúsculas y acentos", () => {
  const prods = [
    { nombre_producto: "Café Americano" },
    { nombre_producto: "Té verde" },
    { nombre_producto: "Jugo" },
  ];
  expect(filtrarProductos(prods, "cafe")).toHaveLength(1);
  expect(filtrarProductos(prods, "CAFÉ")).toHaveLength(1);
  expect(filtrarProductos(prods, "te")).toHaveLength(1);
  expect(filtrarProductos(prods, "")).toHaveLength(3);
  expect(filtrarProductos(prods, "   ")).toHaveLength(3);
  expect(filtrarProductos(prods, "zzz")).toHaveLength(0);
});

test("insumosDisponibles excluye los insumos ya presentes en la receta", () => {
  const insumos = [{ id_insumo: 1 }, { id_insumo: 2 }, { id_insumo: 3 }];
  const receta = [{ id_insumo: 2 }];
  expect(insumosDisponibles(insumos, receta).map((i) => i.id_insumo)).toEqual([1, 3]);
  expect(insumosDisponibles(insumos, [])).toHaveLength(3);
  expect(insumosDisponibles([], receta)).toHaveLength(0);
});
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `cd mobile && npx jest src/lib/recetas.test.ts`
Expected: FAIL — `Cannot find module './recetas'`.

- [ ] **Step 3: Implementar la lógica**

Crear `mobile/src/lib/recetas.ts`:

```typescript
/** Normaliza la coma decimal a punto: los teclados numéricos varían por locale. */
function normalizar(txt: string): string {
  return txt.trim().replace(",", ".");
}

/** Cantidad de receta válida: número > 0 con hasta 3 decimales (lo que acepta la API). */
export function cantidadValida(txt: string): boolean {
  const t = normalizar(txt);
  if (!/^\d+(\.\d{1,3})?$/.test(t)) return false;
  return Number(t) > 0;
}

export function aCantidad(txt: string): number {
  return Number(normalizar(txt));
}

/** Quita acentos y baja a minúsculas para que la búsqueda sea tolerante. */
function plano(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

export function filtrarProductos<T extends { nombre_producto: string }>(
  productos: T[],
  query: string
): T[] {
  const q = plano(query.trim());
  if (q === "") return productos;
  return productos.filter((p) => plano(p.nombre_producto).includes(q));
}

/**
 * Insumos que aún se pueden agregar a la receta. Excluir los ya presentes evita
 * el 409 de la API (un insumo no puede repetirse en la misma receta).
 */
export function insumosDisponibles<T extends { id_insumo: number }>(
  insumos: T[],
  receta: { id_insumo: number }[]
): T[] {
  const usados = new Set(receta.map((l) => l.id_insumo));
  return insumos.filter((i) => !usados.has(i.id_insumo));
}
```

- [ ] **Step 4: Correr los tests y verificar que pasan**

Run: `cd mobile && npx jest src/lib/recetas.test.ts`
Expected: PASS — 4 tests.

- [ ] **Step 5: Commit**

```bash
git add mobile/src/lib/recetas.ts mobile/src/lib/recetas.test.ts
git commit -m "feat(mobile): lógica pura de recetas (validación, filtro e insumos disponibles)"
```

---

### Task 4: Pantalla de lista de productos con receta

**Files:**
- Create: `mobile/src/app/cocina/recetas.tsx`
- Modify: `mobile/src/app/cocina/index.tsx` (enlace "Recetas" en el header)

**Interfaces:**
- Consumes: `getProductos` (ya existe), `filtrarProductos` de Task 3.
- Produces: navegación a `/cocina/receta-detalle?id_producto=<id>&nombre=<nombre>` — Task 5 lee esos params.

- [ ] **Step 1: Crear la pantalla de lista**

Sigue el patrón de `inventario.tsx` (carga con `useFocusEffect`, error con reintento, `FlatList`). Crear `mobile/src/app/cocina/recetas.tsx`:

```typescript
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import { getProductos, Producto } from "@/api/client";
import { filtrarProductos } from "@/lib/recetas";
import { useAuth } from "@/store/auth";

export default function Recetas() {
  const access = useAuth((s) => s.accessToken);
  const [productos, setProductos] = useState<Producto[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      setProductos(await getProductos(access));
    } catch {
      setError("No se pudieron cargar los productos.");
    } finally {
      setLoading(false);
    }
  }, [access]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  const visibles = filtrarProductos(productos, query);

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina" as any)}>
          <Text style={styles.link}>‹ Cocina</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Recetas</Text>
        <View style={{ width: 60 }} />
      </View>

      <TextInput
        style={styles.buscador}
        value={query}
        onChangeText={setQuery}
        placeholder="Buscar producto"
        autoCorrect={false}
      />

      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
      {error && (
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.error}>{error} (tocar para reintentar)</Text>
        </TouchableOpacity>
      )}
      <FlatList
        data={visibles}
        keyExtractor={(p) => String(p.id_producto)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          !loading ? <Text style={styles.muted}>No hay productos.</Text> : null
        }
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              router.push(
                `/cocina/receta-detalle?id_producto=${item.id_producto}&nombre=${encodeURIComponent(
                  item.nombre_producto
                )}` as any
              )
            }
          >
            <Text style={styles.nombre}>{item.nombre_producto}</Text>
            <Text style={styles.chevron}>›</Text>
          </TouchableOpacity>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 12 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 8,
  },
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  buscador: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 10,
    marginBottom: 10,
  },
  list: { gap: 10, paddingBottom: 24 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  nombre: { fontSize: 16, fontWeight: "700", color: "#2d3748", flex: 1 },
  chevron: { fontSize: 22, color: "#a0aec0" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
```

- [ ] **Step 2: Añadir el enlace en el menú de Cocina**

En `mobile/src/app/cocina/index.tsx`, dentro de `<View style={styles.headerActions}>`, añadir antes del `TouchableOpacity` de "Compras":

```typescript
          <TouchableOpacity onPress={() => router.push("/cocina/recetas" as any)}>
            <Text style={styles.link}>Recetas</Text>
          </TouchableOpacity>
```

- [ ] **Step 3: Verificar tipos y suite completa**

Run: `cd mobile && npx tsc --noEmit && npx jest`
Expected: sin errores de tipos; todos los tests siguen pasando (no hay tests de componentes; esto verifica no-regresión).

- [ ] **Step 4: Commit**

```bash
git add mobile/src/app/cocina/recetas.tsx mobile/src/app/cocina/index.tsx
git commit -m "feat(mobile): pantalla de lista de productos para recetas en Cocina"
```

---

### Task 5: Pantalla de detalle con edición inline

**Files:**
- Create: `mobile/src/app/cocina/receta-detalle.tsx`

**Interfaces:**
- Consumes: `getReceta`, `addRecetaLinea`, `patchRecetaLinea`, `deleteRecetaLinea`, `RecetaLinea`, `getInsumos`, `Insumo` (Task 2); `cantidadValida`, `aCantidad`, `insumosDisponibles` (Task 3); params `id_producto` y `nombre` (Task 4).
- Produces: nada — es la hoja del flujo.

- [ ] **Step 1: Crear la pantalla**

Patrón de `ajuste.tsx` (params + carga + `Alert` de error). Crear `mobile/src/app/cocina/receta-detalle.tsx`:

```typescript
import { router, useLocalSearchParams } from "expo-router";
import { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import {
  addRecetaLinea,
  deleteRecetaLinea,
  getInsumos,
  getReceta,
  Insumo,
  patchRecetaLinea,
  RecetaLinea,
} from "@/api/client";
import { aCantidad, cantidadValida, insumosDisponibles } from "@/lib/recetas";
import { useAuth } from "@/store/auth";

export default function RecetaDetalle() {
  const access = useAuth((s) => s.accessToken);
  const { id_producto, nombre } = useLocalSearchParams<{
    id_producto: string;
    nombre: string;
  }>();
  const pid = Number(id_producto);

  const [receta, setReceta] = useState<RecetaLinea[]>([]);
  const [insumos, setInsumos] = useState<Insumo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);

  // Edición inline: id de la línea en edición y su texto de cantidad.
  const [editandoId, setEditandoId] = useState<number | null>(null);
  const [editTxt, setEditTxt] = useState("");

  // Alta de línea nueva.
  const [nuevoInsumo, setNuevoInsumo] = useState<number | null>(null);
  const [nuevaCant, setNuevaCant] = useState("");

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      const [r, i] = await Promise.all([getReceta(access, pid), getInsumos(access)]);
      setReceta(r);
      setInsumos(i);
    } catch {
      setError("No se pudo cargar la receta.");
    } finally {
      setLoading(false);
    }
  }, [access, pid]);

  useEffect(() => {
    cargar();
  }, [cargar]);

  function fallo(e: any, fallback: string) {
    Alert.alert("Error", e?.response?.data?.detail ?? fallback);
  }

  async function guardarEdicion(linea: RecetaLinea) {
    if (!access || !cantidadValida(editTxt)) return;
    setOcupado(true);
    try {
      await patchRecetaLinea(access, pid, linea.id_producto_insumo, aCantidad(editTxt));
      setEditandoId(null);
      setEditTxt("");
      await cargar();
    } catch (e: any) {
      fallo(e, "No se pudo actualizar la cantidad.");
    } finally {
      setOcupado(false);
    }
  }

  function confirmarEliminar(linea: RecetaLinea) {
    Alert.alert(
      "Quitar insumo",
      `¿Quitar ${linea.insumo.nombre_insumo} de la receta?`,
      [
        { text: "Cancelar", style: "cancel" },
        {
          text: "Quitar",
          style: "destructive",
          onPress: async () => {
            if (!access) return;
            setOcupado(true);
            try {
              await deleteRecetaLinea(access, pid, linea.id_producto_insumo);
              await cargar();
            } catch (e: any) {
              fallo(e, "No se pudo quitar el insumo.");
            } finally {
              setOcupado(false);
            }
          },
        },
      ]
    );
  }

  async function agregar() {
    if (!access || nuevoInsumo === null || !cantidadValida(nuevaCant)) return;
    setOcupado(true);
    try {
      await addRecetaLinea(access, pid, {
        id_insumo: nuevoInsumo,
        cantidad_requerida: aCantidad(nuevaCant),
      });
      setNuevoInsumo(null);
      setNuevaCant("");
      await cargar();
    } catch (e: any) {
      fallo(e, "No se pudo agregar el insumo.");
    } finally {
      setOcupado(false);
    }
  }

  const disponibles = insumosDisponibles(insumos, receta);
  const puedeAgregar = nuevoInsumo !== null && cantidadValida(nuevaCant) && !ocupado;

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2b6cb0" />
      </View>
    );
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorTxt}>{error}</Text>
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.link}>Reintentar</Text>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => router.replace("/cocina/recetas" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.replace("/cocina/recetas" as any)}>
          <Text style={styles.link}>‹ Recetas</Text>
        </TouchableOpacity>
        <Text style={styles.title} numberOfLines={1}>
          {nombre ?? "Receta"}
        </Text>
        <View style={{ width: 70 }} />
      </View>
      <Text style={styles.badge}>
        {receta.length === 0
          ? "Sin receta"
          : `${receta.length} ${receta.length === 1 ? "insumo" : "insumos"}`}
      </Text>

      <FlatList
        data={receta}
        keyExtractor={(l) => String(l.id_producto_insumo)}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <Text style={styles.muted}>Este producto no tiene insumos aún.</Text>
        }
        renderItem={({ item }) => {
          const editando = editandoId === item.id_producto_insumo;
          return (
            <View style={styles.card}>
              <Text style={styles.nombre} numberOfLines={1}>
                {item.insumo.nombre_insumo}
              </Text>
              {editando ? (
                <View style={styles.editRow}>
                  <TextInput
                    style={styles.inputMini}
                    keyboardType="numeric"
                    value={editTxt}
                    onChangeText={setEditTxt}
                    autoFocus
                  />
                  <TouchableOpacity
                    disabled={!cantidadValida(editTxt) || ocupado}
                    onPress={() => guardarEdicion(item)}
                  >
                    <Text
                      style={[
                        styles.accion,
                        (!cantidadValida(editTxt) || ocupado) && styles.accionOff,
                      ]}
                    >
                      ✓
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity onPress={() => setEditandoId(null)}>
                    <Text style={styles.accionCancel}>✕</Text>
                  </TouchableOpacity>
                </View>
              ) : (
                <View style={styles.editRow}>
                  <TouchableOpacity
                    disabled={ocupado}
                    onPress={() => {
                      setEditandoId(item.id_producto_insumo);
                      setEditTxt(String(item.cantidad_requerida));
                    }}
                  >
                    <Text style={styles.cantidad}>
                      {item.cantidad_requerida} {item.insumo.unidad.abreviatura}
                    </Text>
                  </TouchableOpacity>
                  <TouchableOpacity disabled={ocupado} onPress={() => confirmarEliminar(item)}>
                    <Text style={styles.quitar}>✕</Text>
                  </TouchableOpacity>
                </View>
              )}
            </View>
          );
        }}
      />

      <View style={styles.pie}>
        <Text style={styles.label}>Agregar insumo</Text>
        {disponibles.length === 0 ? (
          <Text style={styles.muted}>No quedan insumos por agregar.</Text>
        ) : (
          <>
            <FlatList
              horizontal
              data={disponibles}
              keyExtractor={(i) => String(i.id_insumo)}
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.chips}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[styles.chip, nuevoInsumo === item.id_insumo && styles.chipSel]}
                  onPress={() => setNuevoInsumo(item.id_insumo)}
                >
                  <Text
                    style={[
                      styles.chipTxt,
                      nuevoInsumo === item.id_insumo && styles.chipTxtSel,
                    ]}
                  >
                    {item.nombre_insumo}
                  </Text>
                </TouchableOpacity>
              )}
            />
            <View style={styles.editRow}>
              <TextInput
                style={styles.input}
                keyboardType="numeric"
                value={nuevaCant}
                onChangeText={setNuevaCant}
                placeholder="Cantidad"
              />
              <TouchableOpacity
                style={[styles.btn, !puedeAgregar && styles.btnDisabled]}
                disabled={!puedeAgregar}
                onPress={agregar}
              >
                {ocupado ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.btnTxt}>Agregar</Text>
                )}
              </TouchableOpacity>
            </View>
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 12 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 24,
    marginBottom: 4,
  },
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748", flex: 1, textAlign: "center" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  badge: { color: "#718096", marginBottom: 8 },
  list: { gap: 10, paddingBottom: 12 },
  card: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
    gap: 8,
  },
  nombre: { fontSize: 16, fontWeight: "700", color: "#2d3748", flex: 1 },
  editRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  cantidad: { fontSize: 16, color: "#2b6cb0", fontWeight: "600" },
  quitar: { fontSize: 18, color: "#c53030", fontWeight: "700" },
  accion: { fontSize: 18, color: "#2f855a", fontWeight: "700" },
  accionOff: { color: "#a0aec0" },
  accionCancel: { fontSize: 18, color: "#718096", fontWeight: "700" },
  inputMini: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    minWidth: 80,
    textAlign: "right",
  },
  pie: {
    borderTopWidth: 1,
    borderTopColor: "#e2e8f0",
    paddingTop: 12,
    gap: 8,
  },
  label: { fontWeight: "600", color: "#4a5568" },
  chips: { gap: 8, paddingVertical: 4 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: "#fff",
  },
  chipSel: { backgroundColor: "#2b6cb0", borderColor: "#2b6cb0" },
  chipTxt: { color: "#2d3748" },
  chipTxtSel: { color: "#fff", fontWeight: "700" },
  input: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
    flex: 1,
  },
  btn: {
    backgroundColor: "#2b6cb0",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: "center",
    minWidth: 110,
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  muted: { color: "#718096", textAlign: "center", marginVertical: 8 },
  errorTxt: { color: "#c53030", textAlign: "center" },
});
```

- [ ] **Step 2: Verificar tipos y suite completa**

Run: `cd mobile && npx tsc --noEmit && npx jest`
Expected: sin errores de tipos; 74 tests pasando (70 previos + 4 de `recetas.test.ts`).

- [ ] **Step 3: Commit**

```bash
git add mobile/src/app/cocina/receta-detalle.tsx
git commit -m "feat(mobile): detalle de receta con edición inline, alta y baja de insumos"
```

---

### Task 6: Verificación integral y documentación

**Files:**
- Modify: `progress.md`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: bitácora actualizada; rama lista para PR.

- [ ] **Step 1: Suite completa del backend**

Run: `docker compose exec api pytest`
Expected: PASS — 206 tests.

- [ ] **Step 2: Suite completa y tipos del móvil**

Run: `cd mobile && npx tsc --noEmit && npx jest`
Expected: sin errores de tipos; 74 tests pasando.

- [ ] **Step 3: Smoke manual contra la API real**

Levantar el stack y la app:

```bash
docker compose up -d
docker compose exec api python -m app.db.seed
cd mobile && npx expo start
```

Recorrido a verificar (login como `cocinero@cafeteria.com` / `cafeteria123`):
1. Cocina → "Recetas" abre la lista de productos; la búsqueda filtra por nombre (probar con y sin acentos).
2. Abrir un producto sin receta: muestra "Sin receta" y el texto de lista vacía.
3. Agregar un insumo con cantidad `0,25`: aparece la línea y el badge pasa a "1 insumo".
4. Tocar la cantidad, cambiarla a `0.5`, ✓: la línea muestra el valor nuevo.
5. El insumo ya agregado **no** aparece en los chips de "Agregar insumo".
6. ✕ en la línea: pide confirmación y al aceptar la quita.
7. Cantidad inválida (`0`, vacío, `abc`): el botón Agregar y el ✓ quedan deshabilitados.

- [ ] **Step 4: Actualizar `progress.md`**

En la sección "Deuda técnica / mejoras conocidas", reemplazar la línea:

```
- **Recetas** se gestionan solo por API (Swagger); sin pantalla móvil.
```

por:

```
- Recetas: gestión completa desde el móvil (Cocina → Recetas). La lista de productos no muestra el nº de líneas de receta (`GET /productos` no lo trae); se ve al entrar al detalle.
```

Y en la sección "Próximo", registrar el slice terminado y los candidatos siguientes (hardening CSRF app-wide + guard de Ocupada en la API, diferidos del review del PR #21). Actualizar también la fecha y el resumen de "Última actualización" en la cabecera del archivo.

- [ ] **Step 5: Commit**

```bash
git add progress.md
git commit -m "docs: progress.md — recetas en el módulo Cocina móvil"
```

- [ ] **Step 6: Abrir el PR**

```bash
git push -u origin feat/mobile-recetas
gh pr create --base main \
  --title "feat(mobile): pantalla de recetas en Cocina — ver y editar insumos por producto" \
  --body "$(cat <<'EOF'
## Resumen

Cierra el pendiente "Recetas se gestionan solo por API (Swagger); sin pantalla móvil": nuevo flujo **Cocina → Recetas** donde el cocinero ve y edita qué insumos lleva cada producto y en qué cantidad.

- **API**: nuevo `PATCH /productos/{id}/receta/{id_producto_insumo}` para editar la cantidad de una línea (único cambio de backend; el path usa el id de línea igual que el DELETE existente).
- **api-client**: `getReceta`/`addRecetaLinea`/`patchRecetaLinea`/`deleteRecetaLinea` + `cantidad_requerida` añadido a `DECIMAL_FIELDS` (la API la manda como string y sin coacción rompía la aritmética).
- **`lib/recetas.ts`**: lógica pura — validación de cantidad (> 0, hasta 3 decimales, acepta coma), búsqueda de productos tolerante a acentos y mayúsculas, y exclusión de insumos ya usados en el selector (evita el 409 de duplicado en vez de provocarlo).
- **Pantallas**: lista de productos con buscador y detalle con edición inline de cantidad, alta con selector de insumos disponibles y baja con confirmación.
- Spec y plan en `docs/superpowers/`.

## Test plan

- [x] Backend: `docker compose exec api pytest` — 206 (201 previas + 5 del PATCH: feliz, 404 línea, 404 línea de otro producto, 422 cantidad ≤ 0, 403 mesero)
- [x] Móvil: `npx jest` — 74 (70 previas + 4 de `lib/recetas`) y `npx tsc --noEmit` limpio
- [x] Smoke E2E contra la API real: alta, edición inline, baja con confirmación, filtro del selector y búsqueda con acentos
- [ ] Pendiente conocido: la lista de productos no muestra el nº de líneas de receta (`GET /productos` no lo trae); se ve al entrar al detalle

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
