# App móvil Mesero (toma de pedido) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El Mesero aterriza directo en su módulo y completa mesas → menú → carrito → confirmar pedido, consumiendo la API.

**Architecture:** Carrito en un store zustand con helpers puros (testeables con jest); pantallas expo-router con fetch simple; auto-navegación por rol desde la pantalla de carga. Sigue el patrón del slice mobile-auth.

**Tech Stack:** React Native, Expo, expo-router, zustand, axios, jest-expo.

## Global Constraints

- La app móvil corre en el host: `cd mobile && npm test`, `npx tsc --noEmit`, `npx expo start`.
- Token en llamadas: explícito (`access`), obtenido en pantallas con `useAuth((s) => s.accessToken)`.
- Solo mesas con `estado === "Disponible"` inician pedido.
- `precio_venta` llega de la API como **string** (Decimal) → convertir con `Number(...)` al meter al carrito.
- Auto-navegación: `modulesForRole(rol).length === 1` → home directa; si no → `/seleccion-modulo`.
- Código con tests usa imports relativos; las pantallas usan `@/`.

---

### Task 1: Store del carrito

**Files:**
- Create: `mobile/src/store/cart.ts`
- Test: `mobile/src/store/cart.test.ts`

**Interfaces:**
- Produces: `useCart` (zustand); tipos `ProductoCarrito`, `CartItem`; helpers
  `cartTotal(items)`, `cartCount(items)`, `toPayload(state)`; acciones
  `setMesa/addItem/decItem/removeItem/setObservaciones/clear`.

- [ ] **Step 1: Escribir los tests que fallan**

```typescript
// mobile/src/store/cart.test.ts
import { cartCount, cartTotal, toPayload, useCart } from "./cart";

const P = (id: number, precio: number) => ({
  id_producto: id,
  nombre_producto: "P" + id,
  precio_venta: precio,
});

beforeEach(() => {
  useCart.setState({ id_mesa: null, mesa_numero: null, items: [], observaciones: "" });
});

test("addItem agrega y luego incrementa", () => {
  const { addItem } = useCart.getState();
  addItem(P(1, 10));
  addItem(P(1, 10));
  addItem(P(2, 5));
  const items = useCart.getState().items;
  expect(items.length).toBe(2);
  expect(items.find((i) => i.producto.id_producto === 1)!.cantidad).toBe(2);
});

test("decItem baja y a 0 elimina", () => {
  const { addItem, decItem } = useCart.getState();
  addItem(P(1, 10));
  decItem(1);
  expect(useCart.getState().items.length).toBe(0);
});

test("cartTotal y cartCount", () => {
  const { addItem } = useCart.getState();
  addItem(P(1, 10));
  addItem(P(1, 10));
  addItem(P(2, 5));
  const items = useCart.getState().items;
  expect(cartTotal(items)).toBe(25);
  expect(cartCount(items)).toBe(3);
});

test("toPayload arma el cuerpo correcto", () => {
  const { setMesa, addItem, setObservaciones } = useCart.getState();
  setMesa(3, 3);
  addItem(P(1, 10));
  setObservaciones("Sin sal");
  expect(toPayload(useCart.getState())).toEqual({
    id_mesa: 3,
    observaciones: "Sin sal",
    items: [{ id_producto: 1, cantidad: 1, observaciones: null }],
  });
});

test("clear vacía todo", () => {
  const { setMesa, addItem, clear } = useCart.getState();
  setMesa(3, 3);
  addItem(P(1, 10));
  clear();
  const s = useCart.getState();
  expect(s.items.length).toBe(0);
  expect(s.id_mesa).toBeNull();
});
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd mobile && npm test -- cart`
Expected: FAIL (Cannot find module './cart').

- [ ] **Step 3: Implementar `cart.ts`**

```typescript
// mobile/src/store/cart.ts
import { create } from "zustand";

export type ProductoCarrito = {
  id_producto: number;
  nombre_producto: string;
  precio_venta: number;
};

export type CartItem = {
  producto: ProductoCarrito;
  cantidad: number;
  observaciones?: string | null;
};

type CartState = {
  id_mesa: number | null;
  mesa_numero: number | null;
  items: CartItem[];
  observaciones: string;
  setMesa: (id: number, numero: number) => void;
  addItem: (producto: ProductoCarrito) => void;
  decItem: (idProducto: number) => void;
  removeItem: (idProducto: number) => void;
  setObservaciones: (txt: string) => void;
  clear: () => void;
};

export function cartTotal(items: CartItem[]): number {
  return items.reduce((s, it) => s + it.cantidad * it.producto.precio_venta, 0);
}

export function cartCount(items: CartItem[]): number {
  return items.reduce((s, it) => s + it.cantidad, 0);
}

export function toPayload(state: {
  id_mesa: number | null;
  observaciones: string;
  items: CartItem[];
}) {
  return {
    id_mesa: state.id_mesa,
    observaciones: state.observaciones || null,
    items: state.items.map((it) => ({
      id_producto: it.producto.id_producto,
      cantidad: it.cantidad,
      observaciones: it.observaciones ?? null,
    })),
  };
}

export const useCart = create<CartState>((set) => ({
  id_mesa: null,
  mesa_numero: null,
  items: [],
  observaciones: "",

  setMesa: (id, numero) => set({ id_mesa: id, mesa_numero: numero }),

  addItem: (producto) =>
    set((s) => {
      const existe = s.items.find((it) => it.producto.id_producto === producto.id_producto);
      if (existe) {
        return {
          items: s.items.map((it) =>
            it.producto.id_producto === producto.id_producto
              ? { ...it, cantidad: it.cantidad + 1 }
              : it
          ),
        };
      }
      return { items: [...s.items, { producto, cantidad: 1, observaciones: null }] };
    }),

  decItem: (idProducto) =>
    set((s) => ({
      items: s.items
        .map((it) =>
          it.producto.id_producto === idProducto
            ? { ...it, cantidad: it.cantidad - 1 }
            : it
        )
        .filter((it) => it.cantidad > 0),
    })),

  removeItem: (idProducto) =>
    set((s) => ({
      items: s.items.filter((it) => it.producto.id_producto !== idProducto),
    })),

  setObservaciones: (txt) => set({ observaciones: txt }),

  clear: () => set({ id_mesa: null, mesa_numero: null, items: [], observaciones: "" }),
}));
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd mobile && npm test -- cart`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add mobile/src/store/cart.ts mobile/src/store/cart.test.ts
git commit -m "feat(mobile): store del carrito con total y toPayload"
```

---

### Task 2: Extender el API client

**Files:**
- Modify: `mobile/src/api/client.ts`
- Test: `mobile/src/api/client.test.ts` (añadir)

**Interfaces:**
- Produces: tipos `Mesa`, `Categoria`, `Producto`, `CrearPedidoPayload`, `Pedido`;
  `getMesas(access, estado?)`, `getCategorias(access)`,
  `getProductos(access, opts?)`, `crearPedido(access, payload)`.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `mobile/src/api/client.test.ts`:

```typescript
test("getMesas manda bearer y pega a /mesas", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: [{ id_mesa: 1 }] } as any);
  const out = await client.getMesas("tok");
  expect(out).toEqual([{ id_mesa: 1 }]);
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/mesas");
  expect(config.headers.Authorization).toBe("Bearer tok");
});

test("crearPedido postea a /pedidos con el payload", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: { id_pedido: 9 } } as any);
  const payload = { id_mesa: 1, observaciones: null, items: [{ id_producto: 2, cantidad: 1, observaciones: null }] };
  const out = await client.crearPedido("tok", payload);
  expect(out).toEqual({ id_pedido: 9 });
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/pedidos");
  expect(body).toEqual(payload);
  expect(config.headers.Authorization).toBe("Bearer tok");
});
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd mobile && npm test -- client`
Expected: FAIL (client.getMesas is not a function).

- [ ] **Step 3: Añadir tipos, helper y funciones a `client.ts`**

Añadir al final de `mobile/src/api/client.ts`:

```typescript
function authCfg(access: string) {
  return { headers: { Authorization: `Bearer ${access}` } };
}

export type Mesa = {
  id_mesa: number;
  numero_mesa: number;
  capacidad: number;
  ubicacion: string | null;
  estado: string;
};

export type Categoria = {
  id_categoria: number;
  nombre_categoria: string;
  descripcion: string | null;
};

export type Producto = {
  id_producto: number;
  id_categoria: number;
  nombre_producto: string;
  descripcion: string | null;
  precio_venta: number;
  disponible: boolean;
};

export type PedidoItemPayload = {
  id_producto: number;
  cantidad: number;
  observaciones: string | null;
};

export type CrearPedidoPayload = {
  id_mesa: number | null;
  observaciones: string | null;
  items: PedidoItemPayload[];
};

export type Pedido = {
  id_pedido: number;
  id_mesa: number;
  total: number;
  estado: { nombre_estado: string };
};

export async function getMesas(access: string, estado?: string): Promise<Mesa[]> {
  const { data } = await http.get("/mesas", {
    ...authCfg(access),
    params: estado ? { estado } : undefined,
  });
  return data;
}

export async function getCategorias(access: string): Promise<Categoria[]> {
  const { data } = await http.get("/categorias", authCfg(access));
  return data;
}

export async function getProductos(
  access: string,
  opts?: { id_categoria?: number; disponible?: boolean }
): Promise<Producto[]> {
  const { data } = await http.get("/productos", { ...authCfg(access), params: opts });
  return data;
}

export async function crearPedido(
  access: string,
  payload: CrearPedidoPayload
): Promise<Pedido> {
  const { data } = await http.post("/pedidos", payload, authCfg(access));
  return data;
}
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd mobile && npm test -- client`
Expected: PASS (4 tests: 2 previos + 2 nuevos).

- [ ] **Step 5: Commit**

```bash
git add mobile/src/api/client.ts mobile/src/api/client.test.ts
git commit -m "feat(mobile): api client de mesas, categorias, productos y crear pedido"
```

---

### Task 3: Auto-navegación por rol + pantalla de Mesas

**Files:**
- Modify: `mobile/src/lib/modules.ts`, `mobile/src/lib/modules.test.ts`
- Modify: `mobile/src/app/index.tsx`, `mobile/src/app/_layout.tsx`
- Create: `mobile/src/app/mesero/mesas.tsx`
- Verify: `npm test`, `npx tsc --noEmit`

**Interfaces:**
- Consumes: `useAuth`, `useCart`, `getMesas`, `modulesForRole`.
- Produces: ruta `/mesero/mesas` (home del Mesero) y auto-navegación por rol.

- [ ] **Step 1: Actualizar `modules.test.ts` (ruta del Mesero) — test que falla**

Reemplazar la aserción de la ruta en `mobile/src/lib/modules.test.ts`:

```typescript
test("cada modulo apunta a su ruta", () => {
  expect(modulesForRole("Mesero")[0].ruta).toBe("/mesero/mesas");
});
```

Run: `cd mobile && npm test -- modules`
Expected: FAIL (recibe "/modulo/mesero").

- [ ] **Step 2: Cambiar la ruta del Mesero en `modules.ts`**

En `mobile/src/lib/modules.ts`, cambiar la constante `MESERO`:

```typescript
const MESERO: Modulo = { key: "mesero", label: "Mesero", ruta: "/mesero/mesas" };
```

Run: `cd mobile && npm test -- modules`
Expected: PASS.

- [ ] **Step 3: Auto-navegación en `index.tsx`**

```tsx
// mobile/src/app/index.tsx
import { Redirect } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { modulesForRole } from "@/lib/modules";
import { useAuth } from "@/store/auth";

export default function Index() {
  const status = useAuth((s) => s.status);
  const user = useAuth((s) => s.user);
  const bootstrap = useAuth((s) => s.bootstrap);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  if (status === "loading") {
    return (
      <View style={styles.center}>
        <Text style={styles.brand}>☕ Cafetería</Text>
        <ActivityIndicator size="large" color="#2b6cb0" />
      </View>
    );
  }
  if (status === "auth") {
    const modulos = user ? modulesForRole(user.rol.nombre_rol) : [];
    const destino = modulos.length === 1 ? modulos[0].ruta : "/seleccion-modulo";
    return <Redirect href={destino as any} />;
  }
  return <Redirect href={"/login" as any} />;
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    backgroundColor: "#f4f5f7",
  },
  brand: { fontSize: 28, fontWeight: "700", color: "#2d3748" },
});
```

- [ ] **Step 4: Registrar las rutas del Mesero en `_layout.tsx`**

```tsx
// mobile/src/app/_layout.tsx
import { Stack } from "expo-router";

export default function RootLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="index" />
      <Stack.Screen name="login" />
      <Stack.Screen name="seleccion-modulo" />
      <Stack.Screen name="modulo/[key]" />
      <Stack.Screen name="mesero/mesas" />
      <Stack.Screen name="mesero/menu" />
      <Stack.Screen name="mesero/carrito" />
    </Stack>
  );
}
```

- [ ] **Step 5: Crear `mesero/mesas.tsx`**

```tsx
// mobile/src/app/mesero/mesas.tsx
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

import { getMesas, Mesa } from "@/api/client";
import { useAuth } from "@/store/auth";
import { useCart } from "@/store/cart";

export default function Mesas() {
  const access = useAuth((s) => s.accessToken);
  const logout = useAuth((s) => s.logout);
  const setMesa = useCart((s) => s.setMesa);
  const clear = useCart((s) => s.clear);
  const [mesas, setMesas] = useState<Mesa[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const cargar = useCallback(async () => {
    if (!access) return;
    setLoading(true);
    setError(null);
    try {
      setMesas(await getMesas(access));
    } catch {
      setError("No se pudieron cargar las mesas.");
    } finally {
      setLoading(false);
    }
  }, [access]);

  useFocusEffect(
    useCallback(() => {
      cargar();
    }, [cargar])
  );

  function elegir(m: Mesa) {
    clear();
    setMesa(m.id_mesa, m.numero_mesa);
    router.push("/mesero/menu" as any);
  }

  async function salir() {
    await logout();
    router.replace("/login" as any);
  }

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Mesas</Text>
        <TouchableOpacity onPress={salir}>
          <Text style={styles.salir}>Salir</Text>
        </TouchableOpacity>
      </View>
      {loading && <ActivityIndicator size="large" color="#2b6cb0" />}
      {error && (
        <TouchableOpacity onPress={cargar}>
          <Text style={styles.error}>{error} (tocar para reintentar)</Text>
        </TouchableOpacity>
      )}
      <FlatList
        data={mesas}
        keyExtractor={(m) => String(m.id_mesa)}
        numColumns={2}
        columnWrapperStyle={styles.rowGap}
        contentContainerStyle={styles.grid}
        renderItem={({ item }) => {
          const libre = item.estado === "Disponible";
          return (
            <TouchableOpacity
              style={[styles.card, !libre && styles.cardBusy]}
              disabled={!libre}
              onPress={() => elegir(item)}
            >
              <Text style={styles.numero}>Mesa {item.numero_mesa}</Text>
              <Text style={styles.cap}>{item.capacidad} personas</Text>
              <Text style={[styles.badge, libre ? styles.badgeOk : styles.badgeBusy]}>
                {item.estado}
              </Text>
            </TouchableOpacity>
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
  grid: { gap: 12 },
  rowGap: { gap: 12 },
  card: {
    flex: 1,
    backgroundColor: "#fff",
    borderRadius: 12,
    padding: 20,
    alignItems: "center",
    gap: 4,
  },
  cardBusy: { opacity: 0.5 },
  numero: { fontSize: 18, fontWeight: "700", color: "#2d3748" },
  cap: { color: "#718096", fontSize: 13 },
  badge: {
    marginTop: 6,
    paddingHorizontal: 10,
    paddingVertical: 2,
    borderRadius: 999,
    fontSize: 12,
    overflow: "hidden",
  },
  badgeOk: { backgroundColor: "#c6f6d5", color: "#22543d" },
  badgeBusy: { backgroundColor: "#fed7d7", color: "#742a2a" },
  error: { color: "#c53030", textAlign: "center", marginVertical: 8 },
});
```

- [ ] **Step 6: Verificar tipos y tests**

Run: `cd mobile && npx tsc --noEmit && npm test`
Expected: sin errores de tipos; todos los tests PASS (modules + cart + client + auth + session).

- [ ] **Step 7: Commit**

```bash
git add mobile/src/lib/modules.ts mobile/src/lib/modules.test.ts mobile/src/app/index.tsx mobile/src/app/_layout.tsx mobile/src/app/mesero/mesas.tsx
git commit -m "feat(mobile): auto-navegacion por rol y pantalla de mesas"
```

---

### Task 4: Pantallas de Menú y Carrito

**Files:**
- Create: `mobile/src/app/mesero/menu.tsx`, `mobile/src/app/mesero/carrito.tsx`
- Verify: `npx tsc --noEmit`, `npm test`, `npx expo export --platform web`

**Interfaces:**
- Consumes: `useAuth`, `useCart`, `cartTotal/cartCount/toPayload`, `getCategorias/getProductos/crearPedido`.

- [ ] **Step 1: Crear `mesero/menu.tsx`**

```tsx
// mobile/src/app/mesero/menu.tsx
import { router } from "expo-router";
import { useEffect, useState } from "react";
import {
  ActivityIndicator,
  SectionList,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";

import { Categoria, getCategorias, getProductos, Producto } from "@/api/client";
import { useAuth } from "@/store/auth";
import { cartCount, cartTotal, useCart } from "@/store/cart";

export default function Menu() {
  const access = useAuth((s) => s.accessToken);
  const items = useCart((s) => s.items);
  const addItem = useCart((s) => s.addItem);
  const decItem = useCart((s) => s.decItem);
  const [secciones, setSecciones] = useState<{ title: string; data: Producto[] }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!access) return;
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const [cats, prods] = await Promise.all([
          getCategorias(access),
          getProductos(access, { disponible: true }),
        ]);
        const secs = cats
          .map((c: Categoria) => ({
            title: c.nombre_categoria,
            data: prods.filter((p) => p.id_categoria === c.id_categoria),
          }))
          .filter((s) => s.data.length > 0);
        setSecciones(secs);
      } catch {
        setError("No se pudo cargar el menú.");
      } finally {
        setLoading(false);
      }
    })();
  }, [access]);

  function cantidadDe(id: number) {
    return items.find((it) => it.producto.id_producto === id)?.cantidad ?? 0;
  }

  const total = cartTotal(items);
  const count = cartCount(items);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color="#2b6cb0" />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {error && <Text style={styles.error}>{error}</Text>}
      <SectionList
        sections={secciones}
        keyExtractor={(p) => String(p.id_producto)}
        renderSectionHeader={({ section }) => (
          <Text style={styles.sectionH}>{section.title}</Text>
        )}
        renderItem={({ item }) => {
          const n = cantidadDe(item.id_producto);
          return (
            <View style={styles.row}>
              <View style={{ flex: 1 }}>
                <Text style={styles.nombre}>{item.nombre_producto}</Text>
                <Text style={styles.precio}>${item.precio_venta}</Text>
              </View>
              <View style={styles.stepper}>
                <TouchableOpacity style={styles.step} onPress={() => decItem(item.id_producto)}>
                  <Text style={styles.stepTxt}>−</Text>
                </TouchableOpacity>
                <Text style={styles.qty}>{n}</Text>
                <TouchableOpacity
                  style={styles.step}
                  onPress={() =>
                    addItem({
                      id_producto: item.id_producto,
                      nombre_producto: item.nombre_producto,
                      precio_venta: Number(item.precio_venta),
                    })
                  }
                >
                  <Text style={styles.stepTxt}>+</Text>
                </TouchableOpacity>
              </View>
            </View>
          );
        }}
      />
      <TouchableOpacity
        style={[styles.bar, count === 0 && styles.barDisabled]}
        disabled={count === 0}
        onPress={() => router.push("/mesero/carrito" as any)}
      >
        <Text style={styles.barTxt}>
          Ver pedido ({count}) — ${total.toFixed(2)}
        </Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7" },
  center: { flex: 1, alignItems: "center", justifyContent: "center" },
  sectionH: {
    backgroundColor: "#edf2f7",
    paddingHorizontal: 16,
    paddingVertical: 6,
    fontWeight: "700",
    color: "#2d3748",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: "#e2e8f0",
  },
  nombre: { fontSize: 15, color: "#2d3748" },
  precio: { color: "#718096", fontSize: 13 },
  stepper: { flexDirection: "row", alignItems: "center", gap: 10 },
  step: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: "#2b6cb0",
    alignItems: "center",
    justifyContent: "center",
  },
  stepTxt: { color: "#fff", fontSize: 18, fontWeight: "700" },
  qty: { minWidth: 20, textAlign: "center", fontSize: 16 },
  bar: { backgroundColor: "#2b6cb0", padding: 16, alignItems: "center" },
  barDisabled: { backgroundColor: "#a0aec0" },
  barTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
  error: { color: "#c53030", textAlign: "center", padding: 8 },
});
```

- [ ] **Step 2: Crear `mesero/carrito.tsx`**

```tsx
// mobile/src/app/mesero/carrito.tsx
import { router } from "expo-router";
import { useState } from "react";
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

import { crearPedido } from "@/api/client";
import { useAuth } from "@/store/auth";
import { cartTotal, toPayload, useCart } from "@/store/cart";

export default function Carrito() {
  const access = useAuth((s) => s.accessToken);
  const cart = useCart();
  const [enviando, setEnviando] = useState(false);
  const total = cartTotal(cart.items);
  const vacio = cart.items.length === 0;

  async function confirmar() {
    if (!access || vacio) return;
    setEnviando(true);
    try {
      await crearPedido(access, toPayload(useCart.getState()));
      cart.clear();
      Alert.alert("Pedido enviado", "El pedido se envió a cocina.");
      router.replace("/mesero/mesas" as any);
    } catch (e: any) {
      const msg =
        e?.response?.status === 409
          ? "La mesa ya no está disponible."
          : "No se pudo enviar el pedido.";
      Alert.alert("Error", msg);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Pedido — Mesa {cart.mesa_numero ?? ""}</Text>
      <ScrollView>
        {cart.items.map((it) => (
          <View key={it.producto.id_producto} style={styles.row}>
            <Text style={styles.nombre}>{it.producto.nombre_producto}</Text>
            <View style={styles.stepper}>
              <TouchableOpacity style={styles.step} onPress={() => cart.decItem(it.producto.id_producto)}>
                <Text style={styles.stepTxt}>−</Text>
              </TouchableOpacity>
              <Text style={styles.qty}>{it.cantidad}</Text>
              <TouchableOpacity style={styles.step} onPress={() => cart.addItem(it.producto)}>
                <Text style={styles.stepTxt}>+</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.sub}>
              ${(it.cantidad * it.producto.precio_venta).toFixed(2)}
            </Text>
          </View>
        ))}
        {vacio && <Text style={styles.muted}>El carrito está vacío.</Text>}
        <TextInput
          style={styles.obs}
          placeholder="Observaciones del pedido"
          value={cart.observaciones}
          onChangeText={cart.setObservaciones}
        />
      </ScrollView>
      <Text style={styles.total}>Total: ${total.toFixed(2)}</Text>
      <TouchableOpacity
        style={[styles.btn, (vacio || enviando) && styles.btnDisabled]}
        disabled={vacio || enviando}
        onPress={confirmar}
      >
        {enviando ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.btnTxt}>Confirmar pedido</Text>
        )}
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#f4f5f7", padding: 16 },
  title: { fontSize: 20, fontWeight: "700", color: "#2d3748", marginTop: 24, marginBottom: 12 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "#fff",
    padding: 12,
    borderRadius: 8,
    marginBottom: 8,
    gap: 8,
  },
  nombre: { flex: 1, color: "#2d3748" },
  stepper: { flexDirection: "row", alignItems: "center", gap: 10 },
  step: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: "#2b6cb0",
    alignItems: "center",
    justifyContent: "center",
  },
  stepTxt: { color: "#fff", fontSize: 18, fontWeight: "700" },
  qty: { minWidth: 20, textAlign: "center" },
  sub: { minWidth: 64, textAlign: "right", color: "#2d3748", fontWeight: "600" },
  muted: { color: "#718096", textAlign: "center", marginVertical: 16 },
  obs: {
    backgroundColor: "#fff",
    borderWidth: 1,
    borderColor: "#cbd5e0",
    borderRadius: 8,
    padding: 12,
    marginTop: 8,
  },
  total: { fontSize: 18, fontWeight: "700", color: "#2d3748", textAlign: "right", marginVertical: 12 },
  btn: { backgroundColor: "#2b6cb0", padding: 16, borderRadius: 8, alignItems: "center" },
  btnDisabled: { backgroundColor: "#a0aec0" },
  btnTxt: { color: "#fff", fontWeight: "700", fontSize: 16 },
});
```

- [ ] **Step 3: Verificar tipos y tests**

Run: `cd mobile && npx tsc --noEmit && npm test`
Expected: sin errores de tipos; todos los tests PASS.

- [ ] **Step 4: Verificar que empaqueta (web)**

Run: `cd mobile && npx expo export --platform web`
Expected: EXIT 0; bundle de las rutas incluyendo `/mesero/mesas`, `/mesero/menu`, `/mesero/carrito`. Luego `rm -rf dist`.

- [ ] **Step 5: Verificación manual en Expo**

`cd mobile && npx expo start` (o `--web`). Login como `mesero@cafeteria.com` /
`cafeteria123` → aterriza directo en Mesas → elegir una Disponible → menú → +/- → Ver
pedido → Confirmar → aviso y regreso a Mesas con esa mesa Ocupada.

- [ ] **Step 6: Commit**

```bash
git add mobile/src/app/mesero/menu.tsx mobile/src/app/mesero/carrito.tsx
git commit -m "feat(mobile): pantallas de menu y carrito (confirmar pedido)"
```

---

## Cierre

- [ ] Push: `git push -u origin feature/mobile-mesero`
- [ ] Abrir PR hacia `main`.

## Self-Review (cobertura del spec)

- Auto-navegación por rol (RF-M04) → Task 3 (`index.tsx` + `modules.ts`). ✅
- Mesas con estado, solo Disponible inicia (RF-M05..M08) → Task 3 (`mesas.tsx`). ✅
- Menú por categoría + agregar/cantidad/total en vivo (RF-M09..M13) → Task 4 (`menu.tsx`) + Task 1 (helpers). ✅
- Carrito, observaciones, confirmar (RF-M14..M17) → Task 4 (`carrito.tsx`) + Task 2 (`crearPedido`). ✅
- Store del carrito con total y toPayload → Task 1. ✅
- API client (mesas, categorías, productos, crear pedido) → Task 2. ✅
- Manejo de errores (red, 409, carrito vacío) → Tasks 3, 4. ✅
- precio_venta string → Number al carrito → Task 4 (menu addItem). ✅
- Testing jest de la lógica pura → Tasks 1, 2. ✅
- Fuera de alcance (mis pedidos, caja/cocina, pagos): ausente. ✅
