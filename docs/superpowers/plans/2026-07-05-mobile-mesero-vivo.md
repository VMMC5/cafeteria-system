# Móvil Mesero en vivo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pantalla "Mis pedidos" para el Mesero que lista sus pedidos activos en vivo (polling) y permite marcar Entregado los que están Listo.

**Architecture:** Slice casi 100% móvil: el backend ya combina `?mias=true`+`?estados=` y ya permite al Mesero Listo→Entregado (slice 1), así que solo se añade una prueba de regresión. En el móvil se extiende `getPedidos` con `mias`, se añade lógica pura (`lib/mesero.ts`) y una pantalla nueva conectada por un enlace desde Mesas.

**Tech Stack:** FastAPI · pytest (backend) · React Native + Expo Router · Zustand · axios · jest + tsc (móvil).

## Global Constraints

- Backend tests: `docker compose exec -T api pytest ...` (requiere `docker compose up -d`).
- Móvil tests: `cd mobile && npm test` (jest) y `cd mobile && npx tsc --noEmit` (tipos).
- **`mobile/AGENTS.md`:** consultar los docs versionados de Expo v57 (https://docs.expo.dev/versions/v57.0.0/) antes de escribir código móvil. `useFocusEffect` y `router` se importan de `expo-router` (confirmado, sin cambios de ruptura vs. usos actuales).
- Reusar del slice 2: `getEstados`, `cambiarEstadoPedido`, `minutosDesde` (`lib/cocina.ts`), y el patrón de pantalla con `useFocusEffect`+`setInterval`.
- No romper la llamada existente `getPedidos(access, { estados })` (Cocina).
- Estados (nombres exactos, con tilde): `Pendiente`, `En preparación`, `Listo`, `Entregado`, `Cancelado`.

---

### Task 1: Backend — regresión de `?mias=true&estados=`

**Files:**
- Modify: `backend/tests/test_pedidos_api.py` (añadir un test; sin cambios de código de producción)

**Interfaces:**
- Consumes: helpers existentes `_mesa`, `_producto` de `test_pedidos_api.py`; fixtures
  `admin`, `admin_headers`, `mesero`, `mesero_headers`, `cocinero_headers` (conftest);
  endpoints `POST /pedidos`, `PATCH /pedidos/{id}/estado`, `GET /pedidos`.
- Produces: prueba que fija que `GET /pedidos?mias=true&estados=...` devuelve solo los
  pedidos activos del usuario actual.

- [ ] **Step 1: Escribir el test (falla si el combo se rompiera)**

Añadir al final de `backend/tests/test_pedidos_api.py`:

```python
def test_listar_mias_y_estados(
    client, db, admin, admin_headers, mesero, mesero_headers, cocinero_headers
):
    from app.models import EstadoPedido

    def eid(nombre):
        return (
            db.query(EstadoPedido)
            .filter(EstadoPedido.nombre_estado == nombre)
            .one()
            .id_estado
        )

    prod = _producto(client, db, admin_headers)

    # pedido activo del mesero (Pendiente)
    mesa_a = _mesa(client, admin_headers, numero=501)
    p_mesero = client.post(
        "/api/v1/pedidos",
        headers=mesero_headers,
        json={
            "id_mesa": mesa_a["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()

    # pedido de otro usuario (admin)
    mesa_b = _mesa(client, admin_headers, numero=502)
    p_admin = client.post(
        "/api/v1/pedidos",
        headers=admin_headers,
        json={
            "id_mesa": mesa_b["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()

    # pedido del mesero llevado hasta Entregado
    mesa_c = _mesa(client, admin_headers, numero=503)
    p_entregado = client.post(
        "/api/v1/pedidos",
        headers=mesero_headers,
        json={
            "id_mesa": mesa_c["id_mesa"],
            "items": [{"id_producto": prod["id_producto"], "cantidad": 1}],
        },
    ).json()
    pid = p_entregado["id_pedido"]
    client.patch(
        f"/api/v1/pedidos/{pid}/estado",
        headers=cocinero_headers,
        json={"id_estado": eid("En preparación")},
    )
    client.patch(
        f"/api/v1/pedidos/{pid}/estado",
        headers=cocinero_headers,
        json={"id_estado": eid("Listo")},
    )
    client.patch(
        f"/api/v1/pedidos/{pid}/estado",
        headers=mesero_headers,
        json={"id_estado": eid("Entregado")},
    )

    r = client.get(
        f"/api/v1/pedidos?mias=true&estados={eid('Pendiente')},{eid('Listo')}",
        headers=mesero_headers,
    )
    assert r.status_code == 200
    ids = {p["id_pedido"] for p in r.json()}
    assert p_mesero["id_pedido"] in ids
    assert p_admin["id_pedido"] not in ids
    assert p_entregado["id_pedido"] not in ids
```

- [ ] **Step 2: Ejecutar el test**

Run: `docker compose exec -T api pytest tests/test_pedidos_api.py::test_listar_mias_y_estados -v`
Expected: PASS (el backend ya soporta el combo; el test lo fija).

- [ ] **Step 3: Ejecutar la suite backend completa**

Run: `docker compose exec -T api pytest -q`
Expected: PASS (85 previos + 1 = 86).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_pedidos_api.py
git commit -m "test(api): fija listado mias+estados para Mis pedidos del mesero

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Móvil — `getPedidos` con `mias` y lógica de mesero

**Files:**
- Modify: `mobile/src/api/client.ts` (`getPedidos` acepta `{ mias?: boolean }`)
- Modify: `mobile/src/api/client.test.ts` (test del combo mias+estados)
- Create: `mobile/src/lib/mesero.ts`
- Create: `mobile/src/lib/mesero.test.ts`

**Interfaces:**
- Consumes: `http`, `authCfg` (privado en client.ts).
- Produces:
  - `client.getPedidos(access: string, opts?: { estados?: number[]; mias?: boolean }): Promise<Pedido[]>`
  - `mesero.entregable(nombreEstado: string): boolean`
  - `mesero.prioridadEstado(nombreEstado: string): number`

- [ ] **Step 1: Escribir los tests de la lógica de mesero (fallan)**

Crear `mobile/src/lib/mesero.test.ts`:

```typescript
import { entregable, prioridadEstado } from "./mesero";

test("entregable solo para Listo", () => {
  expect(entregable("Listo")).toBe(true);
  expect(entregable("Pendiente")).toBe(false);
  expect(entregable("En preparación")).toBe(false);
});

test("prioridadEstado ordena Listo primero", () => {
  expect(prioridadEstado("Listo")).toBe(0);
  expect(prioridadEstado("En preparación")).toBe(1);
  expect(prioridadEstado("Pendiente")).toBe(2);
  expect(prioridadEstado("Cancelado")).toBe(3);
});
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `cd mobile && npm test -- mesero.test`
Expected: FAIL (no existe `./mesero`).

- [ ] **Step 3: Implementar `lib/mesero.ts`**

Crear `mobile/src/lib/mesero.ts`:

```typescript
export function entregable(nombreEstado: string): boolean {
  return nombreEstado === "Listo";
}

export function prioridadEstado(nombreEstado: string): number {
  const orden: Record<string, number> = {
    Listo: 0,
    "En preparación": 1,
    Pendiente: 2,
  };
  return orden[nombreEstado] ?? 3;
}
```

- [ ] **Step 4: Ejecutar la lógica (pasa)**

Run: `cd mobile && npm test -- mesero.test`
Expected: PASS (2 tests).

- [ ] **Step 5: Escribir el test del cliente (falla)**

Añadir a `mobile/src/api/client.test.ts`:

```typescript
test("getPedidos con mias manda mias y estados", async () => {
  const spy = jest.spyOn(client.http, "get").mockResolvedValue({ data: [] } as any);
  await client.getPedidos("tok", { mias: true, estados: [1, 2, 3] });
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(config.params).toEqual({ estados: "1,2,3", mias: true });
  expect(config.headers.Authorization).toBe("Bearer tok");
});
```

- [ ] **Step 6: Ejecutar para verificar que falla**

Run: `cd mobile && npm test -- client.test`
Expected: FAIL (el test nuevo espera `mias: true` en params; hoy `getPedidos` no lo manda).

- [ ] **Step 7: Extender `getPedidos` en `client.ts`**

En `mobile/src/api/client.ts`, reemplazar la función `getPedidos` por:

```typescript
export async function getPedidos(
  access: string,
  opts?: { estados?: number[]; mias?: boolean }
): Promise<Pedido[]> {
  const params: Record<string, string | boolean> = {};
  if (opts?.estados) params.estados = opts.estados.join(",");
  if (opts?.mias) params.mias = true;
  const { data } = await http.get("/pedidos", {
    ...authCfg(access),
    params: Object.keys(params).length ? params : undefined,
  });
  return data;
}
```

- [ ] **Step 8: Ejecutar los tests del cliente y de lógica (pasan)**

Run: `cd mobile && npm test -- client.test mesero.test`
Expected: PASS (incluye el test de Cocina `getPedidos manda estados como CSV`, que sigue verde porque para `{ estados }` los params son `{ estados: "1,2" }`).

- [ ] **Step 9: Verificar tipos**

Run: `cd mobile && npx tsc --noEmit`
Expected: sin errores.

- [ ] **Step 10: Commit**

```bash
git add mobile/src/api/client.ts mobile/src/api/client.test.ts \
  mobile/src/lib/mesero.ts mobile/src/lib/mesero.test.ts
git commit -m "feat(mobile): getPedidos con mias y lógica de mesero

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Móvil — pantalla "Mis pedidos" y enlace desde Mesas

**Files:**
- Create: `mobile/src/app/mesero/mis-pedidos.tsx`
- Modify: `mobile/src/app/mesero/mesas.tsx` (enlace "Mis pedidos" en el header)
- Modify: `mobile/src/app/_layout.tsx` (registrar `mesero/mis-pedidos`)

**Interfaces:**
- Consumes: `client.getEstados`, `client.getPedidos`, `client.cambiarEstadoPedido`,
  `client.Pedido` (slice 2 + Task 2); `cocina.minutosDesde`; `mesero.entregable`,
  `mesero.prioridadEstado` (Task 2); `useAuth`; `expo-router` (`router`, `useFocusEffect`).
- Produces: ruta `/mesero/mis-pedidos`.

- [ ] **Step 1: Crear la pantalla "Mis pedidos"**

Crear `mobile/src/app/mesero/mis-pedidos.tsx`:

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
import { minutosDesde } from "@/lib/cocina";
import { entregable, prioridadEstado } from "@/lib/mesero";
import { useAuth } from "@/store/auth";

const POLL_MS = 10000;
const ACTIVOS = ["Pendiente", "En preparación", "Listo"];

export default function MisPedidos() {
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
        const ids = ACTIVOS.map((n) => estadoIds.current[n]).filter(
          (x): x is number => typeof x === "number"
        );
        const lista = await getPedidos(access, { mias: true, estados: ids });
        lista.sort((a, b) => {
          const pa = prioridadEstado(a.estado.nombre_estado);
          const pb = prioridadEstado(b.estado.nombre_estado);
          if (pa !== pb) return pa - pb;
          return (
            new Date(a.fecha_pedido).getTime() - new Date(b.fecha_pedido).getTime()
          );
        });
        setPedidos(lista);
      } catch {
        setError("No se pudieron cargar tus pedidos.");
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

  async function entregar(p: Pedido) {
    if (!access) return;
    const destino = estadoIds.current["Entregado"];
    if (destino === undefined) return;
    try {
      await cambiarEstadoPedido(access, p.id_pedido, destino);
    } catch {
      Alert.alert("Aviso", "No se pudo entregar el pedido; se recargó la lista.");
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
        <TouchableOpacity onPress={() => router.replace("/mesero/mesas" as any)}>
          <Text style={styles.link}>‹ Mesas</Text>
        </TouchableOpacity>
        <Text style={styles.title}>Mis pedidos</Text>
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
        <Text style={styles.muted}>No tienes pedidos activos.</Text>
      )}
      <FlatList
        data={pedidos}
        keyExtractor={(p) => String(p.id_pedido)}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => {
          const listo = entregable(item.estado.nombre_estado);
          return (
            <View style={[styles.card, listo && styles.cardListo]}>
              <View style={styles.cardHead}>
                <Text style={styles.mesa}>Mesa {item.mesa.numero_mesa}</Text>
                <Text style={styles.meta}>
                  #{item.id_pedido} · hace {minutosDesde(item.fecha_pedido)} min
                </Text>
              </View>
              {listo ? (
                <Text style={styles.listoTxt}>¡Listo para entregar!</Text>
              ) : (
                <Text style={styles.badge}>{item.estado.nombre_estado}</Text>
              )}
              {item.detalle.map((d, i) => (
                <Text key={i} style={styles.linea}>
                  {d.cantidad} × {d.producto.nombre_producto}
                </Text>
              ))}
              {listo && (
                <TouchableOpacity style={styles.btn} onPress={() => entregar(item)}>
                  <Text style={styles.btnTxt}>Marcar entregado</Text>
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
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748" },
  link: { color: "#2b6cb0", fontWeight: "600" },
  salir: { color: "#c53030", fontWeight: "600" },
  list: { gap: 12, paddingBottom: 24 },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 4 },
  cardListo: { borderWidth: 2, borderColor: "#38a169" },
  cardHead: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  mesa: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  badge: { color: "#4a5568", fontSize: 13, marginVertical: 2 },
  listoTxt: { color: "#22543d", fontWeight: "700", marginVertical: 2 },
  linea: { color: "#2d3748" },
  btn: {
    backgroundColor: "#38a169",
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

- [ ] **Step 2: Añadir el enlace "Mis pedidos" en Mesas**

En `mobile/src/app/mesero/mesas.tsx`, reemplazar el bloque del header:

```tsx
      <View style={styles.header}>
        <Text style={styles.title}>Mesas</Text>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>
```

por:

```tsx
      <View style={styles.header}>
        <Text style={styles.title}>Mesas</Text>
        <View style={styles.headerActions}>
          <TouchableOpacity onPress={() => router.push("/mesero/mis-pedidos" as any)}>
            <Text style={styles.link}>Mis pedidos</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={salir}>
            <Text style={styles.salir}>Salir</Text>
          </TouchableOpacity>
        </View>
      </View>
```

Y en el `StyleSheet.create` de `mesas.tsx`, añadir dos estilos (junto a `salir`):

```tsx
  headerActions: { flexDirection: "row", alignItems: "center", gap: 16 },
  link: { color: "#2b6cb0", fontWeight: "600" },
```

(`router` ya está importado en `mesas.tsx`.)

- [ ] **Step 3: Registrar la pantalla en el layout**

En `mobile/src/app/_layout.tsx`, añadir dentro del `<Stack>` (tras `cocina/index`):

```tsx
      <Stack.Screen name="mesero/mis-pedidos" />
```

- [ ] **Step 4: Verificar tipos y toda la suite móvil**

Run: `cd mobile && npx tsc --noEmit && npm test`
Expected: `tsc` sin errores; jest todo en verde (30 previos + 3 nuevos de Task 2 = 33).

- [ ] **Step 5: Commit**

```bash
git add mobile/src/app/mesero/mis-pedidos.tsx mobile/src/app/mesero/mesas.tsx \
  mobile/src/app/_layout.tsx
git commit -m "feat(mobile): pantalla Mis pedidos del mesero con estado en vivo y entrega

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notas de verificación final (tras Task 3)

- `docker compose exec -T api pytest -q` en verde (86 tests).
- `cd mobile && npm test` en verde (33) y `npx tsc --noEmit` limpio.
- Prueba manual (opcional): login como `mesero@cafeteria.com`, toma un pedido, entra a
  "Mis pedidos" y lo ve en Pendiente; al marcarlo Listo desde Cocina aparece resaltado en
  ≤10 s; "Marcar entregado" lo saca de la lista (la mesa sigue Ocupada).
- `progress.md` se actualiza al cerrar el Sprint 3 (no en este plan).
```
