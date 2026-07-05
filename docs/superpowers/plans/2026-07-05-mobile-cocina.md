# Móvil Cocina — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pantalla de Cocina que lista pedidos activos (Pendiente + En preparación) y permite avanzar su estado por polling, apoyada en dos adiciones de backend (`GET /estados` y `GET /pedidos?estados=1,2`).

**Architecture:** El backend gana un catálogo de estados y filtro multi-estado en el listado de pedidos. El móvil añade funciones de cliente y lógica pura (testeables con jest), y una pantalla nueva `cocina/index.tsx` conectada por Expo Router que consume la API de transiciones del slice 1.

**Tech Stack:** FastAPI · SQLAlchemy · pytest (backend) · React Native + Expo Router · Zustand · axios · jest + tsc (móvil).

## Global Constraints

- Backend tests: `docker compose exec api pytest ...` (requiere `docker compose up -d`).
- Móvil tests: `cd mobile && npm test` (jest) y `cd mobile && npx tsc --noEmit` (tipos).
- **`mobile/AGENTS.md`:** consultar los docs versionados de Expo v57 (https://docs.expo.dev/versions/v57.0.0/) antes de escribir código móvil.
- Seguir patrones existentes: pantallas usan `useFocusEffect`+`useCallback`, `router.replace`, `FlatList`; el cliente usa `authCfg(access)` y `http`.
- No romper la compatibilidad de `GET /pedidos?id_estado=` (filtro por un estado).
- Estados sembrados (nombres exactos, con tilde): `Pendiente`, `En preparación`, `Listo`, `Entregado`, `Cancelado`.

---

### Task 1: Backend — catálogo de estados y filtro multi-estado

**Files:**
- Create: `backend/app/schemas/estado.py`
- Create: `backend/app/api/v1/estados.py`
- Modify: `backend/app/api/v1/router.py`
- Modify: `backend/app/services/pedido_service.py` (`list_pedidos` acepta `estados: list[int] | None`)
- Modify: `backend/app/api/v1/pedidos.py` (endpoint GET añade `estados` CSV)
- Test: `backend/tests/test_cocina_api.py` (crear)

**Interfaces:**
- Consumes: `EstadoPedido`, `Pedido`, `Categoria` de `app.models`; `deps.get_current_user`; endpoints de mesas/productos/pedidos y `PATCH /pedidos/{id}/estado` (slice 1).
- Produces:
  - `GET /api/v1/estados` → `list[EstadoOut]` con `{ id_estado, nombre_estado }`
  - `GET /api/v1/pedidos?estados=1,2` filtra por varios estados (CSV de ids)
  - `pedido_service.list_pedidos(db, estados: list[int] | None = None, id_usuario: int | None = None) -> list[Pedido]`

- [ ] **Step 1: Escribir los tests (fallan)**

Crear `backend/tests/test_cocina_api.py`:

```python
def _estado_id(db, nombre):
    from app.models import EstadoPedido

    return (
        db.query(EstadoPedido)
        .filter(EstadoPedido.nombre_estado == nombre)
        .one()
        .id_estado
    )


def _crear_pedido(client, db, admin_headers, numero):
    from app.models import Categoria

    mesa = client.post(
        "/api/v1/mesas",
        headers=admin_headers,
        json={"numero_mesa": numero, "capacidad": 4},
    ).json()
    cat = db.query(Categoria).first()
    prod = client.post(
        "/api/v1/productos",
        headers=admin_headers,
        json={
            "id_categoria": cat.id_categoria,
            "nombre_producto": "Item",
            "precio_venta": 10.0,
            "disponible": True,
        },
    ).json()
    return client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()


def _avanzar(client, headers, id_pedido, db, nombre_destino):
    return client.patch(
        f"/api/v1/pedidos/{id_pedido}/estado",
        headers=headers,
        json={"id_estado": _estado_id(db, nombre_destino)},
    )


def test_estados_lista(client, admin_headers):
    r = client.get("/api/v1/estados", headers=admin_headers)
    assert r.status_code == 200
    nombres = [e["nombre_estado"] for e in r.json()]
    assert len(r.json()) == 5
    assert "Pendiente" in nombres
    assert "Entregado" in nombres


def test_estados_sin_token_401(client):
    assert client.get("/api/v1/estados").status_code == 401


def test_listar_por_estados_csv(
    client, db, admin_headers, cocinero_headers, mesero_headers
):
    p_pend = _crear_pedido(client, db, admin_headers, numero=401)
    p_prep = _crear_pedido(client, db, admin_headers, numero=402)
    p_entregado = _crear_pedido(client, db, admin_headers, numero=403)

    _avanzar(client, cocinero_headers, p_prep["id_pedido"], db, "En preparación")
    _avanzar(client, cocinero_headers, p_entregado["id_pedido"], db, "En preparación")
    _avanzar(client, cocinero_headers, p_entregado["id_pedido"], db, "Listo")
    _avanzar(client, mesero_headers, p_entregado["id_pedido"], db, "Entregado")

    pend_id = _estado_id(db, "Pendiente")
    prep_id = _estado_id(db, "En preparación")
    r = client.get(
        f"/api/v1/pedidos?estados={pend_id},{prep_id}", headers=admin_headers
    )
    assert r.status_code == 200
    ids = {p["id_pedido"] for p in r.json()}
    assert p_pend["id_pedido"] in ids
    assert p_prep["id_pedido"] in ids
    assert p_entregado["id_pedido"] not in ids


def test_listar_id_estado_compat(client, db, admin_headers):
    p = _crear_pedido(client, db, admin_headers, numero=410)
    pend_id = _estado_id(db, "Pendiente")
    r = client.get(f"/api/v1/pedidos?id_estado={pend_id}", headers=admin_headers)
    assert r.status_code == 200
    assert all(x["estado"]["nombre_estado"] == "Pendiente" for x in r.json())
    assert any(x["id_pedido"] == p["id_pedido"] for x in r.json())
```

- [ ] **Step 2: Ejecutar los tests para verificar que fallan**

Run: `docker compose exec -T api pytest tests/test_cocina_api.py -v`
Expected: FAIL (`/estados` da 404; `?estados=` aún no filtra).

- [ ] **Step 3: Crear el schema `EstadoOut`**

Crear `backend/app/schemas/estado.py`:

```python
from pydantic import BaseModel, ConfigDict


class EstadoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_estado: int
    nombre_estado: str
```

- [ ] **Step 4: Crear el router `GET /estados`**

Crear `backend/app/api/v1/estados.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import EstadoPedido, Usuario
from app.schemas.estado import EstadoOut

router = APIRouter(prefix="/estados", tags=["estados"])


@router.get("", response_model=list[EstadoOut])
def listar(
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return list(
        db.execute(select(EstadoPedido).order_by(EstadoPedido.id_estado)).scalars()
    )
```

- [ ] **Step 5: Registrar el router**

En `backend/app/api/v1/router.py`, actualizar el import y el include:

```python
from app.api.v1 import (
    auth,
    categorias,
    estados,
    mesas,
    pedidos,
    productos,
    roles,
    usuarios,
)
```

Y tras `api_router.include_router(pedidos.router)`:

```python
api_router.include_router(estados.router)
```

- [ ] **Step 6: `list_pedidos` acepta varios estados**

En `backend/app/services/pedido_service.py`, reemplazar la función `list_pedidos` por:

```python
def list_pedidos(
    db: Session,
    estados: list[int] | None = None,
    id_usuario: int | None = None,
) -> list[Pedido]:
    stmt = select(Pedido).order_by(Pedido.id_pedido.desc())
    if estados:
        stmt = stmt.where(Pedido.id_estado.in_(estados))
    if id_usuario is not None:
        stmt = stmt.where(Pedido.id_usuario == id_usuario)
    return list(db.execute(stmt).scalars())
```

- [ ] **Step 7: El endpoint GET soporta `?estados=1,2`**

En `backend/app/api/v1/pedidos.py`, reemplazar el endpoint `listar` por:

```python
@router.get("", response_model=list[PedidoOut])
def listar(
    id_estado: int | None = None,
    estados: str | None = None,
    mias: bool = False,
    db: Session = Depends(get_db),
    current: Usuario = Depends(deps.get_current_user),
):
    id_usuario = current.id_usuario if mias else None
    if estados:
        ids = [int(x) for x in estados.split(",") if x.strip()]
    elif id_estado is not None:
        ids = [id_estado]
    else:
        ids = None
    return pedido_service.list_pedidos(db, ids, id_usuario)
```

- [ ] **Step 8: Ejecutar los tests de cocina (pasan)**

Run: `docker compose exec -T api pytest tests/test_cocina_api.py -v`
Expected: PASS (4 tests).

- [ ] **Step 9: Ejecutar la suite backend completa (sin regresiones)**

Run: `docker compose exec -T api pytest -q`
Expected: PASS (81 previos + 4 nuevos = 85).

- [ ] **Step 10: Commit**

```bash
git add backend/app/schemas/estado.py backend/app/api/v1/estados.py \
  backend/app/api/v1/router.py backend/app/services/pedido_service.py \
  backend/app/api/v1/pedidos.py backend/tests/test_cocina_api.py
git commit -m "feat(api): catálogo de estados y filtro multi-estado en pedidos

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Móvil — cliente API y lógica de cocina

**Files:**
- Modify: `mobile/src/api/client.ts` (tipos `Estado`, `Pedido` extendido; `getEstados`, `getPedidos`, `cambiarEstadoPedido`)
- Modify: `mobile/src/api/client.test.ts` (tests de las 3 funciones)
- Create: `mobile/src/lib/cocina.ts` (`minutosDesde`, `accionCocina`)
- Create: `mobile/src/lib/cocina.test.ts`

**Interfaces:**
- Consumes: `http`, `authCfg` (privado en client.ts) — se reusan dentro del módulo.
- Produces:
  - `client.Estado = { id_estado: number; nombre_estado: string }`
  - `client.Pedido` extendido con `mesa`, `estado {id_estado, nombre_estado}`, `fecha_pedido`, `detalle`, `observaciones`
  - `client.getEstados(access: string): Promise<Estado[]>`
  - `client.getPedidos(access: string, opts?: { estados?: number[] }): Promise<Pedido[]>`
  - `client.cambiarEstadoPedido(access: string, id_pedido: number, id_estado: number): Promise<Pedido>`
  - `cocina.minutosDesde(fechaISO: string, ahora?: Date): number`
  - `cocina.accionCocina(nombreEstado: string): { label: string; destinoNombre: string } | null`

- [ ] **Step 1: Escribir los tests de la lógica de cocina (fallan)**

Crear `mobile/src/lib/cocina.test.ts`:

```typescript
import { accionCocina, minutosDesde } from "./cocina";

test("minutosDesde calcula minutos enteros", () => {
  const ahora = new Date("2026-07-05T12:30:00Z");
  expect(minutosDesde("2026-07-05T12:00:00Z", ahora)).toBe(30);
});

test("minutosDesde nunca es negativo", () => {
  const ahora = new Date("2026-07-05T12:00:00Z");
  expect(minutosDesde("2026-07-05T12:05:00Z", ahora)).toBe(0);
});

test("accionCocina mapea Pendiente y En preparación", () => {
  expect(accionCocina("Pendiente")).toEqual({
    label: "Iniciar preparación",
    destinoNombre: "En preparación",
  });
  expect(accionCocina("En preparación")).toEqual({
    label: "Marcar listo",
    destinoNombre: "Listo",
  });
});

test("accionCocina devuelve null para Listo o desconocido", () => {
  expect(accionCocina("Listo")).toBeNull();
  expect(accionCocina("Cualquiera")).toBeNull();
});
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `cd mobile && npm test -- cocina.test`
Expected: FAIL (no existe `./cocina`).

- [ ] **Step 3: Implementar `lib/cocina.ts`**

Crear `mobile/src/lib/cocina.ts`:

```typescript
export function minutosDesde(fechaISO: string, ahora: Date = new Date()): number {
  const ms = ahora.getTime() - new Date(fechaISO).getTime();
  return Math.max(0, Math.floor(ms / 60000));
}

export type AccionCocina = { label: string; destinoNombre: string };

export function accionCocina(nombreEstado: string): AccionCocina | null {
  if (nombreEstado === "Pendiente") {
    return { label: "Iniciar preparación", destinoNombre: "En preparación" };
  }
  if (nombreEstado === "En preparación") {
    return { label: "Marcar listo", destinoNombre: "Listo" };
  }
  return null;
}
```

- [ ] **Step 4: Ejecutar la lógica (pasa)**

Run: `cd mobile && npm test -- cocina.test`
Expected: PASS (4 tests).

- [ ] **Step 5: Escribir los tests del cliente (fallan)**

Añadir a `mobile/src/api/client.test.ts`:

```typescript
test("getEstados pega a /estados con bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [{ id_estado: 1, nombre_estado: "Pendiente" }] } as any);
  const out = await client.getEstados("tok");
  expect(out).toEqual([{ id_estado: 1, nombre_estado: "Pendiente" }]);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/estados");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getPedidos manda estados como CSV", async () => {
  const spy = jest.spyOn(client.http, "get").mockResolvedValue({ data: [] } as any);
  await client.getPedidos("tok", { estados: [1, 2] });
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(config.params).toEqual({ estados: "1,2" });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("cambiarEstadoPedido hace PATCH con id_estado", async () => {
  const spy = jest
    .spyOn(client.http, "patch")
    .mockResolvedValue({ data: { id_pedido: 5 } } as any);
  await client.cambiarEstadoPedido("tok", 5, 3);
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos/5/estado");
  expect(body).toEqual({ id_estado: 3 });
  expect(config.headers.Authorization).toBe("Bearer tok");
});
```

- [ ] **Step 6: Ejecutar para verificar que fallan**

Run: `cd mobile && npm test -- client.test`
Expected: FAIL (`getEstados`/`getPedidos`/`cambiarEstadoPedido` no existen).

- [ ] **Step 7: Extender `client.ts`**

En `mobile/src/api/client.ts`, reemplazar el bloque del type `Pedido` (actualmente
`export type Pedido = { id_pedido; id_mesa; total; estado: { nombre_estado } };`) por:

```typescript
export type Estado = { id_estado: number; nombre_estado: string };

export type PedidoLinea = {
  cantidad: number;
  observaciones: string | null;
  producto: { nombre_producto: string };
};

export type Pedido = {
  id_pedido: number;
  id_mesa: number;
  mesa: { numero_mesa: number };
  estado: { id_estado: number; nombre_estado: string };
  fecha_pedido: string;
  observaciones: string | null;
  detalle: PedidoLinea[];
  total: number;
};
```

Y al final del archivo, añadir las tres funciones:

```typescript
export async function getEstados(access: string): Promise<Estado[]> {
  const { data } = await http.get("/estados", authCfg(access));
  return data;
}

export async function getPedidos(
  access: string,
  opts?: { estados?: number[] }
): Promise<Pedido[]> {
  const params = opts?.estados ? { estados: opts.estados.join(",") } : undefined;
  const { data } = await http.get("/pedidos", { ...authCfg(access), params });
  return data;
}

export async function cambiarEstadoPedido(
  access: string,
  id_pedido: number,
  id_estado: number
): Promise<Pedido> {
  const { data } = await http.patch(
    `/pedidos/${id_pedido}/estado`,
    { id_estado },
    authCfg(access)
  );
  return data;
}
```

Nota: `crearPedido` sigue devolviendo `Pedido`; la API ya retorna el `PedidoOut`
completo, así que el type extendido es correcto.

- [ ] **Step 8: Ejecutar los tests del cliente y de lógica (pasan)**

Run: `cd mobile && npm test -- client.test cocina.test`
Expected: PASS.

- [ ] **Step 9: Verificar tipos**

Run: `cd mobile && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 10: Commit**

```bash
git add mobile/src/api/client.ts mobile/src/api/client.test.ts \
  mobile/src/lib/cocina.ts mobile/src/lib/cocina.test.ts
git commit -m "feat(mobile): cliente de estados/pedidos y lógica de cocina

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Móvil — pantalla de Cocina y navegación

**Files:**
- Create: `mobile/src/app/cocina/index.tsx`
- Modify: `mobile/src/app/_layout.tsx` (registrar `cocina/index`)
- Modify: `mobile/src/lib/modules.ts` (`COCINA.ruta` → `/cocina`)
- Modify: `mobile/src/lib/modules.test.ts` (aserción de la ruta de cocina)

**Interfaces:**
- Consumes: `client.getEstados`, `client.getPedidos`, `client.cambiarEstadoPedido`,
  `client.Pedido` (Task 2); `cocina.accionCocina`, `cocina.minutosDesde` (Task 2);
  `useAuth` store; `expo-router` (`router`, `useFocusEffect`).
- Produces: ruta `/cocina` (pantalla del rol Cocinero).

- [ ] **Step 1: Actualizar el test de módulos (falla)**

En `mobile/src/lib/modules.test.ts`, reemplazar el test `"cada modulo apunta a su ruta"`
por una versión que también verifique cocina:

```typescript
test("cada modulo apunta a su ruta", () => {
  expect(modulesForRole("Mesero")[0].ruta).toBe("/mesero/mesas");
  expect(modulesForRole("Cocinero")[0].ruta).toBe("/cocina");
});
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `cd mobile && npm test -- modules.test`
Expected: FAIL (`COCINA.ruta` sigue siendo `/modulo/cocina`).

- [ ] **Step 3: Cambiar la ruta de COCINA**

En `mobile/src/lib/modules.ts`, cambiar la línea de `COCINA`:

```typescript
const COCINA: Modulo = { key: "cocina", label: "Cocina", ruta: "/cocina" };
```

- [ ] **Step 4: Ejecutar el test de módulos (pasa)**

Run: `cd mobile && npm test -- modules.test`
Expected: PASS.

- [ ] **Step 5: Crear la pantalla de Cocina**

Crear `mobile/src/app/cocina/index.tsx`:

```tsx
import { router, useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { cambiarEstadoPedido, getEstados, getPedidos, Pedido } from "@/api/client";
import { accionCocina, minutosDesde } from "@/lib/cocina";
import { useAuth } from "@/store/auth";

const POLL_MS = 10000;

export default function Cocina() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const estadoIds = useRef<Record<string, number>>({});

  const cargar = useCallback(
    async (mostrarSpinner: boolean) => {
      if (!access) return;
      if (mostrarSpinner) setLoading(true);
      setError(null);
      try {
        if (Object.keys(estadoIds.current).length === 0) {
          const estados = await getEstados(access);
          estadoIds.current = Object.fromEntries(
            estados.map((e) => [e.nombre_estado, e.id_estado])
          );
        }
        const activos = [
          estadoIds.current["Pendiente"],
          estadoIds.current["En preparación"],
        ].filter((x): x is number => typeof x === "number");
        const lista = await getPedidos(access, { estados: activos });
        lista.sort(
          (a, b) =>
            new Date(a.fecha_pedido).getTime() - new Date(b.fecha_pedido).getTime()
        );
        setPedidos(lista);
      } catch {
        setError("No se pudieron cargar los pedidos.");
      } finally {
        if (mostrarSpinner) setLoading(false);
      }
    },
    [access]
  );

  useFocusEffect(
    useCallback(() => {
      cargar(true);
      const id = setInterval(() => cargar(false), POLL_MS);
      return () => clearInterval(id);
    }, [cargar])
  );

  async function avanzar(p: Pedido) {
    const accion = accionCocina(p.estado.nombre_estado);
    if (!access || !accion) return;
    const destino = estadoIds.current[accion.destinoNombre];
    if (destino === undefined) return;
    try {
      await cambiarEstadoPedido(access, p.id_pedido, destino);
    } catch {
      Alert.alert("Aviso", "No se pudo actualizar el pedido; se recargó la lista.");
    } finally {
      cargar(false);
    }
  }

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Cocina</Text>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>
      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
      {error && (
        <TouchableOpacity onPress={() => cargar(true)}>
          <Text style={styles.error}>{error} (tocar para reintentar)</Text>
        </TouchableOpacity>
      )}
      {!loading && !error && pedidos.length === 0 && (
        <Text style={styles.muted}>No hay pedidos activos.</Text>
      )}
      <FlatList
        data={pedidos}
        keyExtractor={(p) => String(p.id_pedido)}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => {
          const accion = accionCocina(item.estado.nombre_estado);
          const pend = item.estado.nombre_estado === "Pendiente";
          return (
            <View style={styles.card}>
              <View style={styles.cardHead}>
                <Text style={styles.mesa}>Mesa {item.mesa.numero_mesa}</Text>
                <Text style={styles.meta}>
                  #{item.id_pedido} · hace {minutosDesde(item.fecha_pedido)} min
                </Text>
              </View>
              <Text style={[styles.badge, pend ? styles.badgePend : styles.badgePrep]}>
                {item.estado.nombre_estado}
              </Text>
              {item.detalle.map((d, i) => (
                <Text key={i} style={styles.linea}>
                  {d.cantidad} × {d.producto.nombre_producto}
                  {d.observaciones ? `  (${d.observaciones})` : ""}
                </Text>
              ))}
              {item.observaciones ? (
                <Text style={styles.obs}>Nota: {item.observaciones}</Text>
              ) : null}
              {accion && (
                <TouchableOpacity style={styles.btn} onPress={() => avanzar(item)}>
                  <Text style={styles.btnTxt}>{accion.label}</Text>
                </TouchableOpacity>
              )}
            </View>
          );
        }}
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
  title: { fontSize: 24, fontWeight: "700", color: "#2d3748" },
  salir: { color: "#c53030", fontWeight: "600" },
  list: { gap: 12, paddingBottom: 24 },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 4 },
  cardHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  mesa: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  badge: {
    alignSelf: "flex-start",
    marginVertical: 4,
    paddingHorizontal: 10,
    paddingVertical: 2,
    borderRadius: 999,
    fontSize: 12,
    overflow: "hidden",
  },
  badgePend: { backgroundColor: "#feebc8", color: "#7b341e" },
  badgePrep: { backgroundColor: "#bee3f8", color: "#2a4365" },
  linea: { color: "#2d3748" },
  obs: { color: "#718096", fontStyle: "italic" },
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 12,
    borderRadius: 8,
    alignItems: "center",
    marginTop: 8,
  },
  btnTxt: { color: "#fff", fontWeight: "700" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
```

- [ ] **Step 6: Registrar la pantalla en el layout**

En `mobile/src/app/_layout.tsx`, añadir dentro del `<Stack>` (tras `mesero/carrito`):

```tsx
      <Stack.Screen name="cocina/index" />
```

- [ ] **Step 7: Verificar tipos y toda la suite móvil**

Run: `cd mobile && npx tsc --noEmit && npm test`
Expected: `tsc` sin errores; jest todo en verde (23 previos + 7 nuevos de Task 2 + ajuste de modules).

- [ ] **Step 8: Commit**

```bash
git add mobile/src/app/cocina/index.tsx mobile/src/app/_layout.tsx \
  mobile/src/lib/modules.ts mobile/src/lib/modules.test.ts
git commit -m "feat(mobile): pantalla de Cocina con polling y avance de estado

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notas de verificación final (tras Task 3)

- `docker compose exec -T api pytest -q` en verde (85 tests).
- `cd mobile && npm test` en verde y `npx tsc --noEmit` limpio.
- Prueba manual (opcional): login como `cocinero@cafeteria.com`, aterriza en `/cocina`,
  ve pedidos activos, "Iniciar preparación"/"Marcar listo" avanzan y el pedido Listo
  desaparece; con un pedido creado desde Mesero aparece en cocina en ≤10 s.
- `progress.md` se actualiza al cerrar el slice (no en este plan).
```
