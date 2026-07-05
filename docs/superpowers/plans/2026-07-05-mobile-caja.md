# Móvil Caja — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pantallas de Caja para cobrar pedidos: lista de pendientes de cobro, pantalla de cobro (método + monto + cambio) y comprobante inline con desglose de IVA, apoyadas en un `GET /metodos_pago` nuevo.

**Architecture:** El backend gana un catálogo de métodos de pago. El móvil añade tipos/funciones de cliente y lógica pura (testeables con jest) y dos pantallas conectadas por Expo Router que consumen la API de cobro del slice 1.

**Tech Stack:** FastAPI · pytest (backend) · React Native + Expo Router · Zustand · axios · jest + tsc (móvil).

## Global Constraints

- Backend tests: `docker compose exec -T api pytest ...` (requiere `docker compose up -d`).
- Móvil tests: `cd mobile && npm test` (jest) y `cd mobile && npx tsc --noEmit` (tipos).
- **`mobile/AGENTS.md`:** consultar los docs de Expo v57 (https://docs.expo.dev/versions/v57.0.0/) antes de escribir código móvil. `router`, `useFocusEffect`, `useLocalSearchParams` se importan de `expo-router` (usados ya en el código actual).
- Reusar patrones: pantallas con `useFocusEffect`+`setInterval` (Cocina), `authCfg(access)` en el cliente, chips/inputs como en Mesero.
- No romper llamadas existentes de `getPedidos` (Cocina usa `{estados}`, Mesero `{mias,estados}`).
- La API serializa `Decimal` como número JSON (los campos `total`/`subtotal`/`iva`/`cambio`/`monto` llegan como `number`).

---

### Task 1: Backend — `GET /metodos_pago`

**Files:**
- Create: `backend/app/api/v1/metodos_pago.py`
- Modify: `backend/app/api/v1/router.py`
- Test: `backend/tests/test_metodos_pago_api.py` (crear)

**Interfaces:**
- Consumes: `MetodoPago`, `Usuario` de `app.models`; `schemas.venta.MetodoResumen`
  (`{id_metodo_pago, nombre_metodo}`, del slice 1); `deps.get_current_user`.
- Produces: `GET /api/v1/metodos_pago` → `list[MetodoResumen]`.

- [ ] **Step 1: Escribir los tests (fallan)**

Crear `backend/tests/test_metodos_pago_api.py`:

```python
def test_metodos_lista(client, admin_headers):
    r = client.get("/api/v1/metodos_pago", headers=admin_headers)
    assert r.status_code == 200
    nombres = [m["nombre_metodo"] for m in r.json()]
    assert len(r.json()) == 4
    assert "Efectivo" in nombres


def test_metodos_sin_token_401(client):
    assert client.get("/api/v1/metodos_pago").status_code == 401
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `docker compose exec -T api pytest tests/test_metodos_pago_api.py -v`
Expected: FAIL (404 — la ruta no existe).

- [ ] **Step 3: Crear el router `metodos_pago.py`**

Crear `backend/app/api/v1/metodos_pago.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import deps
from app.db.session import get_db
from app.models import MetodoPago, Usuario
from app.schemas.venta import MetodoResumen

router = APIRouter(prefix="/metodos_pago", tags=["metodos_pago"])


@router.get("", response_model=list[MetodoResumen])
def listar(
    db: Session = Depends(get_db),
    _: Usuario = Depends(deps.get_current_user),
):
    return list(
        db.execute(
            select(MetodoPago).order_by(MetodoPago.id_metodo_pago)
        ).scalars()
    )
```

- [ ] **Step 4: Registrar el router**

En `backend/app/api/v1/router.py`, añadir `metodos_pago` al import (orden alfabético) y al
include tras `ventas`:

```python
from app.api.v1 import (
    auth,
    categorias,
    estados,
    mesas,
    metodos_pago,
    pedidos,
    productos,
    roles,
    usuarios,
    ventas,
)
```

```python
api_router.include_router(metodos_pago.router)
```

- [ ] **Step 5: Ejecutar los tests (pasan) y la suite**

Run: `docker compose exec -T api pytest tests/test_metodos_pago_api.py -v && docker compose exec -T api pytest -q`
Expected: 2 nuevos en verde; suite completa (98 previos + 2 = 100).

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/metodos_pago.py backend/app/api/v1/router.py \
  backend/tests/test_metodos_pago_api.py
git commit -m "feat(api): catálogo GET /metodos_pago

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: Móvil — cliente de ventas y lógica de caja

**Files:**
- Modify: `mobile/src/api/client.ts`
- Modify: `mobile/src/api/client.test.ts`
- Create: `mobile/src/lib/caja.ts`
- Create: `mobile/src/lib/caja.test.ts`

**Interfaces:**
- Consumes: `http`, `authCfg` (privados en client.ts); type `Pedido` (existente).
- Produces:
  - Tipos `MetodoPago`, `PagoOut`, `Venta`
  - `client.getMetodosPago(access): Promise<MetodoPago[]>`
  - `client.getPedidos(access, opts?: { estados?; mias?; por_cobrar? }): Promise<Pedido[]>`
  - `client.getPedido(access, id: number): Promise<Pedido>`
  - `client.cobrarVenta(access, id_pedido: number, pagos: { id_metodo_pago: number; monto: number }[]): Promise<Venta>`
  - `caja.cambio(recibido: number, total: number): number`
  - `caja.puedeCobrar(recibido: number, total: number): boolean`

- [ ] **Step 1: Escribir los tests de la lógica de caja (fallan)**

Crear `mobile/src/lib/caja.test.ts`:

```typescript
import { cambio, puedeCobrar } from "./caja";

test("cambio = recibido - total, nunca negativo", () => {
  expect(cambio(200, 116)).toBe(84);
  expect(cambio(100, 116)).toBe(0);
});

test("puedeCobrar exige recibido >= total y total > 0", () => {
  expect(puedeCobrar(116, 116)).toBe(true);
  expect(puedeCobrar(200, 116)).toBe(true);
  expect(puedeCobrar(100, 116)).toBe(false);
  expect(puedeCobrar(0, 0)).toBe(false);
});
```

- [ ] **Step 2: Ejecutar para verificar que fallan**

Run: `cd mobile && npm test -- caja.test`
Expected: FAIL (no existe `./caja`).

- [ ] **Step 3: Implementar `lib/caja.ts`**

Crear `mobile/src/lib/caja.ts`:

```typescript
export function cambio(recibido: number, total: number): number {
  return Math.max(0, recibido - total);
}

export function puedeCobrar(recibido: number, total: number): boolean {
  return total > 0 && recibido >= total;
}
```

- [ ] **Step 4: Ejecutar la lógica (pasa)**

Run: `cd mobile && npm test -- caja.test`
Expected: PASS (2 tests).

- [ ] **Step 5: Escribir los tests del cliente (fallan)**

Añadir a `mobile/src/api/client.test.ts`:

```typescript
test("getMetodosPago pega a /metodos_pago con bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [{ id_metodo_pago: 1, nombre_metodo: "Efectivo" }] } as any);
  const out = await client.getMetodosPago("tok");
  expect(out).toEqual([{ id_metodo_pago: 1, nombre_metodo: "Efectivo" }]);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/metodos_pago");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("getPedidos con por_cobrar manda el flag", async () => {
  const spy = jest.spyOn(client.http, "get").mockResolvedValue({ data: [] } as any);
  await client.getPedidos("tok", { por_cobrar: true });
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(config.params).toEqual({ por_cobrar: true });
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("cobrarVenta postea a /ventas con id_pedido y pagos", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: { id_venta: 3 } } as any);
  await client.cobrarVenta("tok", 7, [{ id_metodo_pago: 1, monto: 200 }]);
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/ventas");
  expect(body).toEqual({ id_pedido: 7, pagos: [{ id_metodo_pago: 1, monto: 200 }] });
  expect(config.headers.Authorization).toBe("Bearer tok");
});
```

- [ ] **Step 6: Ejecutar para verificar que fallan**

Run: `cd mobile && npm test -- client.test`
Expected: FAIL (`getMetodosPago`/`cobrarVenta` no existen; `getPedidos` no manda `por_cobrar`).

- [ ] **Step 7: Extender `client.ts` — tipos**

En `mobile/src/api/client.ts`, tras el type `Pedido` (que termina en `total: number; };`),
añadir:

```typescript
export type MetodoPago = { id_metodo_pago: number; nombre_metodo: string };

export type PagoOut = {
  id_pago: number;
  id_metodo_pago: number;
  metodo: { nombre_metodo: string };
  monto: number;
  referencia: string | null;
};

export type Venta = {
  id_venta: number;
  id_pedido: number;
  folio: string;
  estado_venta: string;
  fecha_venta: string;
  total: number;
  subtotal: number;
  iva: number;
  cambio: number;
  pagos: PagoOut[];
};
```

- [ ] **Step 8: Extender `client.ts` — `getPedidos` y funciones nuevas**

Reemplazar la función `getPedidos` por (añade `por_cobrar`):

```typescript
export async function getPedidos(
  access: string,
  opts?: { estados?: number[]; mias?: boolean; por_cobrar?: boolean }
): Promise<Pedido[]> {
  const params: Record<string, string | boolean> = {};
  if (opts?.estados) params.estados = opts.estados.join(",");
  if (opts?.mias) params.mias = true;
  if (opts?.por_cobrar) params.por_cobrar = true;
  const { data } = await http.get("/pedidos", {
    ...authCfg(access),
    params: Object.keys(params).length ? params : undefined,
  });
  return data;
}
```

Y al final del archivo, añadir:

```typescript
export async function getMetodosPago(access: string): Promise<MetodoPago[]> {
  const { data } = await http.get("/metodos_pago", authCfg(access));
  return data;
}

export async function getPedido(access: string, id: number): Promise<Pedido> {
  const { data } = await http.get(`/pedidos/${id}`, authCfg(access));
  return data;
}

export async function cobrarVenta(
  access: string,
  id_pedido: number,
  pagos: { id_metodo_pago: number; monto: number }[]
): Promise<Venta> {
  const { data } = await http.post("/ventas", { id_pedido, pagos }, authCfg(access));
  return data;
}
```

- [ ] **Step 9: Ejecutar tests cliente + lógica y tipos**

Run: `cd mobile && npm test -- client.test caja.test && npx tsc --noEmit`
Expected: PASS; `tsc` sin errores.

- [ ] **Step 10: Commit**

```bash
git add mobile/src/api/client.ts mobile/src/api/client.test.ts \
  mobile/src/lib/caja.ts mobile/src/lib/caja.test.ts
git commit -m "feat(mobile): cliente de ventas/métodos y lógica de caja

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Móvil — pantallas de Caja y navegación

**Files:**
- Create: `mobile/src/app/caja/index.tsx`
- Create: `mobile/src/app/caja/cobro.tsx`
- Modify: `mobile/src/app/_layout.tsx`
- Modify: `mobile/src/lib/modules.ts`
- Modify: `mobile/src/lib/modules.test.ts`

**Interfaces:**
- Consumes: `client.getPedidos`, `client.getPedido`, `client.getMetodosPago`,
  `client.cobrarVenta`, tipos `Pedido`/`MetodoPago`/`Venta` (Task 2); `caja.cambio`,
  `caja.puedeCobrar` (Task 2); `useAuth`; `expo-router`
  (`router`, `useFocusEffect`, `useLocalSearchParams`).
- Produces: rutas `/caja` y `/caja/cobro`.

- [ ] **Step 1: Actualizar el test de módulos para la ruta de caja (falla)**

En `mobile/src/lib/modules.test.ts`, en el test
`"homeRoute: rol de un solo modulo va directo a su home"`, cambiar la aserción de Cajero:

```typescript
test("homeRoute: rol de un solo modulo va directo a su home", () => {
  expect(homeRoute("Mesero")).toBe("/mesero/mesas");
  expect(homeRoute("Cajero")).toBe("/caja");
});
```

- [ ] **Step 2: Ejecutar para verificar que falla**

Run: `cd mobile && npm test -- modules.test`
Expected: FAIL (`CAJA.ruta` sigue siendo `/modulo/caja`).

- [ ] **Step 3: Cambiar la ruta de CAJA**

En `mobile/src/lib/modules.ts`, cambiar la línea de `CAJA`:

```typescript
const CAJA: Modulo = { key: "caja", label: "Caja", ruta: "/caja" };
```

- [ ] **Step 4: Ejecutar el test de módulos (pasa)**

Run: `cd mobile && npm test -- modules.test`
Expected: PASS.

- [ ] **Step 5: Crear la pantalla de pendientes `caja/index.tsx`**

Crear `mobile/src/app/caja/index.tsx`:

```tsx
import { router, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { getPedidos, Pedido } from "@/api/client";
import { useAuth } from "@/store/auth";

const POLL_MS = 10000;

export default function Caja() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const [pedidos, setPedidos] = useState<Pedido[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(
    async (mostrarSpinner: boolean) => {
      if (!access) return;
      if (mostrarSpinner) setLoading(true);
      setError(null);
      try {
        setPedidos(await getPedidos(access, { por_cobrar: true }));
      } catch {
        setError("No se pudieron cargar los pendientes de cobro.");
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

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Caja — por cobrar</Text>
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
        <Text style={styles.muted}>No hay pedidos por cobrar.</Text>
      )}
      <FlatList
        data={pedidos}
        keyExtractor={(p) => String(p.id_pedido)}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() =>
              router.push(`/caja/cobro?id_pedido=${item.id_pedido}` as any)
            }
          >
            <View>
              <Text style={styles.mesa}>Mesa {item.mesa.numero_mesa}</Text>
              <Text style={styles.meta}>#{item.id_pedido}</Text>
            </View>
            <Text style={styles.total}>${item.total.toFixed(2)}</Text>
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
  title: { fontSize: 22, fontWeight: "700", color: "#2d3748" },
  salir: { color: "#c53030", fontWeight: "600" },
  list: { gap: 12, paddingBottom: 24 },
  card: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 16,
  },
  mesa: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  meta: { color: "#718096", fontSize: 13 },
  total: { fontSize: 18, fontWeight: "700", color: "#2b6cb0" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
```

- [ ] **Step 6: Crear la pantalla de cobro `caja/cobro.tsx`**

Crear `mobile/src/app/caja/cobro.tsx`:

```tsx
import { router, useLocalSearchParams } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";

import {
  cobrarVenta,
  getMetodosPago,
  getPedido,
  MetodoPago,
  Pedido,
  Venta,
} from "@/api/client";
import { cambio, puedeCobrar } from "@/lib/caja";
import { useAuth } from "@/store/auth";

function Row({
  label,
  value,
  bold,
}: {
  label: string;
  value: number;
  bold?: boolean;
}) {
  return (
    <View style={styles.row}>
      <Text style={[styles.rowL, bold && styles.bold]}>{label}</Text>
      <Text style={[styles.rowV, bold && styles.bold]}>${value.toFixed(2)}</Text>
    </View>
  );
}

export default function Cobro() {
  const access = useAuth((s) => s.accessToken);
  const { id_pedido } = useLocalSearchParams<{ id_pedido: string }>();
  const pid = Number(id_pedido);
  const [pedido, setPedido] = useState<Pedido | null>(null);
  const [metodos, setMetodos] = useState<MetodoPago[]>([]);
  const [metodoSel, setMetodoSel] = useState<number | null>(null);
  const [recibidoTxt, setRecibidoTxt] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cobrando, setCobrando] = useState(false);
  const [venta, setVenta] = useState<Venta | null>(null);

  useEffect(() => {
    if (!access) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [p, ms] = await Promise.all([
          getPedido(access, pid),
          getMetodosPago(access),
        ]);
        setPedido(p);
        setMetodos(ms);
        if (ms.length > 0) setMetodoSel(ms[0].id_metodo_pago);
      } catch {
        setError("No se pudo cargar el cobro.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access, pid]);

  const total = pedido?.total ?? 0;
  const recibido = Number(recibidoTxt) || 0;
  const habilitado = metodoSel !== null && puedeCobrar(recibido, total);

  async function confirmar() {
    if (!access || metodoSel === null || !habilitado) return;
    setCobrando(true);
    try {
      const v = await cobrarVenta(access, pid, [
        { id_metodo_pago: metodoSel, monto: recibido },
      ]);
      setVenta(v);
    } catch (e: any) {
      const msg =
        e?.response?.status === 409
          ? "El pedido ya no está disponible para cobro."
          : "No se pudo cobrar.";
      Alert.alert("Error", msg, [
        { text: "OK", onPress: () => router.replace("/caja" as any) },
      ]);
    } finally {
      setCobrando(false);
    }
  }

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
        <TouchableOpacity onPress={() => router.replace("/caja" as any)}>
          <Text style={styles.link}>Volver</Text>
        </TouchableOpacity>
      </View>
    );
  }

  if (venta) {
    return (
      <View style={styles.container}>
        <Text style={styles.title}>Comprobante</Text>
        <View style={styles.ticket}>
          <Text style={styles.folio}>Folio {venta.folio}</Text>
          <Row label="Subtotal" value={venta.subtotal} />
          <Row label="IVA" value={venta.iva} />
          <Row label="Total" value={venta.total} bold />
          <View style={styles.sep} />
          {venta.pagos.map((pg) => (
            <Row key={pg.id_pago} label={pg.metodo.nombre_metodo} value={pg.monto} />
          ))}
          <Row label="Cambio" value={venta.cambio} bold />
        </View>
        <TouchableOpacity
          style={styles.btn}
          onPress={() => router.replace("/caja" as any)}
        >
          <Text style={styles.btnTxt}>Terminar</Text>
        </TouchableOpacity>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Cobro — Mesa {pedido?.mesa.numero_mesa}</Text>
      <ScrollView>
        {pedido?.detalle.map((d, i) => (
          <Text key={i} style={styles.linea}>
            {d.cantidad} × {d.producto.nombre_producto}
          </Text>
        ))}
        <Text style={styles.total}>Total: ${total.toFixed(2)}</Text>

        <Text style={styles.label}>Método de pago</Text>
        <View style={styles.chips}>
          {metodos.map((m) => {
            const sel = metodoSel === m.id_metodo_pago;
            return (
              <TouchableOpacity
                key={m.id_metodo_pago}
                style={[styles.chip, sel && styles.chipSel]}
                onPress={() => setMetodoSel(m.id_metodo_pago)}
              >
                <Text style={[styles.chipTxt, sel && styles.chipTxtSel]}>
                  {m.nombre_metodo}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={styles.label}>Monto recibido</Text>
        <TextInput
          style={styles.input}
          keyboardType="numeric"
          value={recibidoTxt}
          onChangeText={setRecibidoTxt}
          placeholder="0.00"
        />
        <Text style={styles.cambio}>Cambio: ${cambio(recibido, total).toFixed(2)}</Text>
      </ScrollView>
      <TouchableOpacity
        style={[styles.btn, (!habilitado || cobrando) && styles.btnDisabled]}
        disabled={!habilitado || cobrando}
        onPress={confirmar}
      >
        {cobrando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnTxt}>Confirmar cobro</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 16 },
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12 },
  title: {
    fontSize: 20,
    fontWeight: "700",
    color: "#2d3748",
    marginTop: 24,
    marginBottom: 12,
  },
  linea: { color: "#2d3748", paddingVertical: 2 },
  total: {
    fontSize: 18,
    fontWeight: "700",
    color: "#2d3748",
    textAlign: "right",
    marginVertical: 12,
  },
  label: { fontWeight: "600", color: "#4a5568", marginTop: 8, marginBottom: 6 },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: {
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
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
  },
  cambio: {
    fontSize: 16,
    fontWeight: "700",
    color: "#22543d",
    marginTop: 10,
    textAlign: "right",
  },
  ticket: { backgroundColor: "#fff", borderRadius: 12, padding: 16, gap: 6 },
  folio: { fontWeight: "700", color: "#2d3748", marginBottom: 6 },
  row: { flexDirection: "row", justifyContent: "space-between" },
  rowL: { color: "#4a5568" },
  rowV: { color: "#2d3748" },
  bold: { fontWeight: "700" },
  sep: { height: 1, backgroundColor: "#e2e8f0", marginVertical: 6 },
  btn: {
    backgroundColor: "#2b6cb0",
    padding: 16,
    borderRadius: 8,
    alignItems: "center",
  },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  errorTxt: { color: "#c53030", textAlign: "center" },
  link: { color: "#2b6cb0", fontWeight: "600" },
});
```

- [ ] **Step 7: Registrar las pantallas en el layout**

En `mobile/src/app/_layout.tsx`, añadir dentro del `<Stack>` (tras
`mesero/mis-pedidos`):

```tsx
      <Stack.Screen name="caja/index" />
      <Stack.Screen name="caja/cobro" />
```

- [ ] **Step 8: Verificar tipos y toda la suite móvil**

Run: `cd mobile && npx tsc --noEmit && npm test`
Expected: `tsc` sin errores; jest en verde (33 previos + 5 nuevos de Task 2 = 38; `modules.test` sigue en verde con la aserción actualizada).

- [ ] **Step 9: Commit**

```bash
git add mobile/src/app/caja/index.tsx mobile/src/app/caja/cobro.tsx \
  mobile/src/app/_layout.tsx mobile/src/lib/modules.ts mobile/src/lib/modules.test.ts
git commit -m "feat(mobile): pantallas de Caja (cobro y comprobante)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Notas de verificación final (tras Task 3)

- `docker compose exec -T api pytest -q` en verde (100 tests).
- `cd mobile && npm test` en verde (38) y `npx tsc --noEmit` limpio.
- Prueba manual (opcional): login como `cajero@cafeteria.com`, aterriza en `/caja`, ve un
  pedido por cobrar, entra al cobro, elige Efectivo, ingresa un monto ≥ total, ve el cambio,
  confirma → aparece el comprobante con folio y desglose de IVA; el pedido cobrado
  desaparece de pendientes y la mesa queda Disponible.
- `progress.md` se actualiza al cerrar el Sprint 4 (no en este plan).
```
