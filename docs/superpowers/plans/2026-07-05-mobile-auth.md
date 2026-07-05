# App móvil (carga, login, selección de módulo) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La app Expo arranca con pantalla de carga, permite login con sesión persistida y muestra selección de módulo según rol.

**Architecture:** expo-router (Stack) con guard de sesión; zustand para el estado de auth; `expo-secure-store` persiste los tokens; axios contra la API. Lógica pura (client, store, mapeo rol→módulo) cubierta con jest-expo; pantallas verificadas manualmente.

**Tech Stack:** React Native, Expo, expo-router, zustand, axios, expo-secure-store, jest-expo.

## Global Constraints

- La app móvil corre en el **host** (no en Docker): comandos `cd mobile && npm test`, `npx tsc --noEmit`, `npx expo start`.
- URL de la API vía `process.env.EXPO_PUBLIC_API_BASE_URL` (Expo inyecta vars con prefijo `EXPO_PUBLIC_`).
- `/auth/me` devuelve el usuario con `rol` anidado (`user.rol.nombre_rol`).
- Rol→módulo: Mesero→[Mesero], Cajero→[Caja], Cocinero→[Cocina], Administrador→[los 3], otro→[].
- Rutas de módulo: `/modulo/<key>` (key ∈ mesero|caja|cocina). Nada de grupos `(mesero)/` (colisionan con `/`).
- Código con tests usa imports **relativos** (sin alias `@/`) para simplificar jest; las pantallas pueden usar `@/`.

---

### Task 1: Config de entorno + jest + mapeo rol→módulo

**Files:**
- Create: `mobile/.env`, `mobile/.env.example`
- Modify: `mobile/package.json` (jest config + script `test`)
- Create: `mobile/src/lib/modules.ts`
- Test: `mobile/src/lib/modules.test.ts`

**Interfaces:**
- Produces: `Modulo = { key: "mesero"|"caja"|"cocina"; label: string; ruta: string }`;
  `modulesForRole(rol: string): Modulo[]`.

- [ ] **Step 1: Crear `.env` y `.env.example`**

`mobile/.env` (ignorado por git):
```
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

`mobile/.env.example`:
```
# URL base de la API FastAPI.
# - Web (npm run web):            http://localhost:8000/api/v1
# - Emulador Android:             http://10.0.2.2:8000/api/v1
# - Dispositivo físico (Expo Go): http://<IP-LAN-de-tu-PC>:8000/api/v1  (ej. 192.168.1.20)
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

- [ ] **Step 2: Instalar jest-expo**

Run:
```bash
cd mobile && npx expo install jest-expo && npm install --save-dev jest @types/jest
```

- [ ] **Step 3: Añadir config de jest y script a `package.json`**

Añadir el script `test` dentro de `"scripts"`:
```json
    "test": "jest"
```
Añadir en la raíz del `package.json` la clave `jest`:
```json
  "jest": {
    "preset": "jest-expo"
  }
```

- [ ] **Step 4: Escribir el test que falla**

```typescript
// mobile/src/lib/modules.test.ts
import { modulesForRole } from "./modules";

test("mesero ve solo su modulo", () => {
  const m = modulesForRole("Mesero");
  expect(m.map((x) => x.key)).toEqual(["mesero"]);
});

test("cajero ve caja, cocinero ve cocina", () => {
  expect(modulesForRole("Cajero").map((x) => x.key)).toEqual(["caja"]);
  expect(modulesForRole("Cocinero").map((x) => x.key)).toEqual(["cocina"]);
});

test("administrador ve los tres modulos", () => {
  expect(modulesForRole("Administrador").map((x) => x.key)).toEqual([
    "mesero", "caja", "cocina",
  ]);
});

test("rol desconocido no ve modulos", () => {
  expect(modulesForRole("Otro")).toEqual([]);
});

test("cada modulo apunta a /modulo/<key>", () => {
  expect(modulesForRole("Mesero")[0].ruta).toBe("/modulo/mesero");
});
```

- [ ] **Step 5: Correr y verificar que falla**

Run: `cd mobile && npm test -- modules`
Expected: FAIL (Cannot find module './modules').

- [ ] **Step 6: Implementar `modules.ts`**

```typescript
// mobile/src/lib/modules.ts
export type Modulo = {
  key: "mesero" | "caja" | "cocina";
  label: string;
  ruta: string;
};

const MESERO: Modulo = { key: "mesero", label: "Mesero", ruta: "/modulo/mesero" };
const CAJA: Modulo = { key: "caja", label: "Caja", ruta: "/modulo/caja" };
const COCINA: Modulo = { key: "cocina", label: "Cocina", ruta: "/modulo/cocina" };

export function modulesForRole(rol: string): Modulo[] {
  switch (rol) {
    case "Mesero":
      return [MESERO];
    case "Cajero":
      return [CAJA];
    case "Cocinero":
      return [COCINA];
    case "Administrador":
      return [MESERO, CAJA, COCINA];
    default:
      return [];
  }
}
```

- [ ] **Step 7: Correr y verificar que pasa**

Run: `cd mobile && npm test -- modules`
Expected: PASS (5 tests).

- [ ] **Step 8: Commit**

```bash
git add mobile/.env.example mobile/package.json mobile/package-lock.json mobile/src/lib/modules.ts mobile/src/lib/modules.test.ts
git commit -m "feat(mobile): config de API, jest-expo y mapeo rol->modulo"
```

---

### Task 2: Persistencia (secure-store) y cliente de API

**Files:**
- Create: `mobile/src/lib/session.ts`
- Create: `mobile/src/api/client.ts`
- Test: `mobile/src/api/client.test.ts`

**Interfaces:**
- Produces:
  - `session.saveTokens(access, refresh): Promise<void>`,
    `session.loadTokens(): Promise<{access,refresh}|null>`,
    `session.clearTokens(): Promise<void>`.
  - `client.http` (instancia axios), tipos `Tokens`, `Rol`, `Usuario`,
    `client.login(correo, password): Promise<Tokens>`,
    `client.getMe(access): Promise<Usuario>`,
    `client.refresh(refreshToken): Promise<Tokens>`.

- [ ] **Step 1: Escribir el test que falla**

```typescript
// mobile/src/api/client.test.ts
import * as client from "./client";

test("login postea form urlencoded y devuelve tokens", async () => {
  const spy = jest
    .spyOn(client.http, "post")
    .mockResolvedValue({ data: { access_token: "a", refresh_token: "r" } } as any);
  const out = await client.login("admin@cafeteria.com", "secret123");
  expect(out.access_token).toBe("a");
  const [url, body, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/auth/login");
  expect(String(body)).toContain("username=admin%40cafeteria.com");
  expect(config.headers["Content-Type"]).toBe("application/x-www-form-urlencoded");
});

test("getMe manda el Bearer", async () => {
  const spy = jest
    .spyOn(client.http, "get")
    .mockResolvedValue({ data: { id_usuario: 1 } } as any);
  await client.getMe("tok");
  const [url, config] = spy.mock.calls[0] as any[];
  expect(url).toBe("/auth/me");
  expect(config.headers.Authorization).toBe("Bearer tok");
});
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd mobile && npm test -- client`
Expected: FAIL (Cannot find module './client').

- [ ] **Step 3: Implementar `session.ts`**

```typescript
// mobile/src/lib/session.ts
import * as SecureStore from "expo-secure-store";

const ACCESS = "access_token";
const REFRESH = "refresh_token";

export async function saveTokens(access: string, refresh: string): Promise<void> {
  await SecureStore.setItemAsync(ACCESS, access);
  await SecureStore.setItemAsync(REFRESH, refresh);
}

export async function loadTokens(): Promise<{ access: string; refresh: string } | null> {
  const access = await SecureStore.getItemAsync(ACCESS);
  const refresh = await SecureStore.getItemAsync(REFRESH);
  if (!access || !refresh) return null;
  return { access, refresh };
}

export async function clearTokens(): Promise<void> {
  await SecureStore.deleteItemAsync(ACCESS);
  await SecureStore.deleteItemAsync(REFRESH);
}
```

- [ ] **Step 4: Implementar `client.ts`**

```typescript
// mobile/src/api/client.ts
import axios from "axios";

const baseURL =
  process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

export const http = axios.create({ baseURL, timeout: 10000 });

export type Tokens = { access_token: string; refresh_token: string };
export type Rol = { id_rol: number; nombre_rol: string; descripcion: string | null };
export type Usuario = {
  id_usuario: number;
  nombre: string;
  apellido_paterno: string;
  apellido_materno: string | null;
  correo: string;
  nombre_usuario: string;
  id_rol: number;
  rol: Rol;
  activo: boolean;
};

export async function login(correo: string, password: string): Promise<Tokens> {
  const body = new URLSearchParams({ username: correo, password });
  const { data } = await http.post("/auth/login", body.toString(), {
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  });
  return data;
}

export async function getMe(access: string): Promise<Usuario> {
  const { data } = await http.get("/auth/me", {
    headers: { Authorization: `Bearer ${access}` },
  });
  return data;
}

export async function refresh(refreshToken: string): Promise<Tokens> {
  const { data } = await http.post("/auth/refresh", {
    refresh_token: refreshToken,
  });
  return data;
}
```

- [ ] **Step 5: Correr y verificar que pasa**

Run: `cd mobile && npm test -- client`
Expected: PASS (2 tests).

- [ ] **Step 6: Commit**

```bash
git add mobile/src/lib/session.ts mobile/src/api/client.ts mobile/src/api/client.test.ts
git commit -m "feat(mobile): secure-store y cliente axios de la API"
```

---

### Task 3: Store de autenticación (zustand)

**Files:**
- Create: `mobile/src/store/auth.ts`
- Test: `mobile/src/store/auth.test.ts`

**Interfaces:**
- Consumes: `client.login/getMe/refresh`, `session.saveTokens/loadTokens/clearTokens`.
- Produces: `useAuth` (zustand store) con estado
  `{ status: "loading"|"auth"|"noauth", user, accessToken, refreshToken }` y acciones
  `bootstrap()`, `login(correo, password)`, `logout()`.

- [ ] **Step 1: Escribir el test que falla**

```typescript
// mobile/src/store/auth.test.ts
jest.mock("../api/client");
jest.mock("../lib/session");

import * as client from "../api/client";
import * as session from "../lib/session";
import { useAuth } from "./auth";

beforeEach(() => {
  jest.clearAllMocks();
  useAuth.setState({
    status: "loading", user: null, accessToken: null, refreshToken: null,
  });
});

test("login guarda tokens y pone status auth", async () => {
  (client.login as jest.Mock).mockResolvedValue({ access_token: "a", refresh_token: "r" });
  (client.getMe as jest.Mock).mockResolvedValue({ id_usuario: 1, rol: { nombre_rol: "Mesero" } });
  await useAuth.getState().login("m@cafeteria.com", "secret123");
  expect(session.saveTokens).toHaveBeenCalledWith("a", "r");
  expect(useAuth.getState().status).toBe("auth");
  expect(useAuth.getState().user?.rol.nombre_rol).toBe("Mesero");
});

test("bootstrap sin tokens -> noauth", async () => {
  (session.loadTokens as jest.Mock).mockResolvedValue(null);
  await useAuth.getState().bootstrap();
  expect(useAuth.getState().status).toBe("noauth");
});

test("bootstrap con token valido -> auth", async () => {
  (session.loadTokens as jest.Mock).mockResolvedValue({ access: "a", refresh: "r" });
  (client.getMe as jest.Mock).mockResolvedValue({ id_usuario: 1, rol: { nombre_rol: "Cajero" } });
  await useAuth.getState().bootstrap();
  expect(useAuth.getState().status).toBe("auth");
});

test("logout limpia el estado", async () => {
  useAuth.setState({ status: "auth", user: { id_usuario: 1 } as any, accessToken: "a", refreshToken: "r" });
  await useAuth.getState().logout();
  expect(session.clearTokens).toHaveBeenCalled();
  expect(useAuth.getState().status).toBe("noauth");
  expect(useAuth.getState().user).toBeNull();
});
```

- [ ] **Step 2: Correr y verificar que falla**

Run: `cd mobile && npm test -- auth`
Expected: FAIL (Cannot find module './auth').

- [ ] **Step 3: Implementar `auth.ts`**

```typescript
// mobile/src/store/auth.ts
import { create } from "zustand";

import * as client from "../api/client";
import { clearTokens, loadTokens, saveTokens } from "../lib/session";

type Status = "loading" | "auth" | "noauth";

type AuthState = {
  status: Status;
  user: client.Usuario | null;
  accessToken: string | null;
  refreshToken: string | null;
  bootstrap: () => Promise<void>;
  login: (correo: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuth = create<AuthState>((set) => ({
  status: "loading",
  user: null,
  accessToken: null,
  refreshToken: null,

  bootstrap: async () => {
    const tokens = await loadTokens();
    if (!tokens) {
      set({ status: "noauth" });
      return;
    }
    try {
      const user = await client.getMe(tokens.access);
      set({ status: "auth", user, accessToken: tokens.access, refreshToken: tokens.refresh });
    } catch {
      try {
        const nt = await client.refresh(tokens.refresh);
        await saveTokens(nt.access_token, nt.refresh_token);
        const user = await client.getMe(nt.access_token);
        set({ status: "auth", user, accessToken: nt.access_token, refreshToken: nt.refresh_token });
      } catch {
        await clearTokens();
        set({ status: "noauth", user: null, accessToken: null, refreshToken: null });
      }
    }
  },

  login: async (correo, password) => {
    const t = await client.login(correo, password);
    await saveTokens(t.access_token, t.refresh_token);
    const user = await client.getMe(t.access_token);
    set({ status: "auth", user, accessToken: t.access_token, refreshToken: t.refresh_token });
  },

  logout: async () => {
    await clearTokens();
    set({ status: "noauth", user: null, accessToken: null, refreshToken: null });
  },
}));
```

- [ ] **Step 4: Correr y verificar que pasa**

Run: `cd mobile && npm test -- auth`
Expected: PASS (4 tests).

- [ ] **Step 5: Correr toda la suite**

Run: `cd mobile && npm test`
Expected: PASS (11 tests: 5 modules + 2 client + 4 auth).

- [ ] **Step 6: Commit**

```bash
git add mobile/src/store/auth.ts mobile/src/store/auth.test.ts
git commit -m "feat(mobile): store de autenticacion con zustand (bootstrap/login/logout)"
```

---

### Task 4: Pantallas y navegación (expo-router)

**Files:**
- Modify: `mobile/src/app/_layout.tsx`
- Create/replace: `mobile/src/app/index.tsx`
- Create: `mobile/src/app/login.tsx`, `mobile/src/app/seleccion-modulo.tsx`, `mobile/src/app/modulo/[key].tsx`
- Delete: `mobile/src/app/explore.tsx`
- Verify: `npx tsc --noEmit` + arranque manual en Expo

**Interfaces:**
- Consumes: `useAuth` (store), `modulesForRole`.
- Produces las pantallas de la navegación.

- [ ] **Step 1: Reescribir `_layout.tsx` (Stack sin tabs demo)**

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
    </Stack>
  );
}
```

- [ ] **Step 2: Reescribir `index.tsx` (pantalla de carga, RF-M27/M28)**

```tsx
// mobile/src/app/index.tsx
import { Redirect } from "expo-router";
import { useEffect } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { useAuth } from "@/store/auth";

export default function Index() {
  const status = useAuth((s) => s.status);
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
  return <Redirect href={status === "auth" ? "/seleccion-modulo" : "/login"} />;
}

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: "center", justifyContent: "center", gap: 16, backgroundColor: "#f4f5f7" },
  brand: { fontSize: 28, fontWeight: "700", color: "#2d3748" },
});
```

- [ ] **Step 3: Crear `login.tsx` (RF-M01/M02)**

```tsx
// mobile/src/app/login.tsx
import { router } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from "react-native";

import { useAuth } from "@/store/auth";

export default function Login() {
  const login = useAuth((s) => s.login);
  const [correo, setCorreo] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit() {
    setError(null);
    setLoading(true);
    try {
      await login(correo.trim(), password);
      router.replace("/seleccion-modulo");
    } catch (e: any) {
      if (e?.response?.status === 401) setError("Correo o contraseña incorrectos.");
      else setError("No se pudo conectar con el servidor.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.brand}>☕ Cafetería</Text>
      <Text style={styles.title}>Iniciar sesión</Text>
      {error && <Text style={styles.error}>{error}</Text>}
      <TextInput
        style={styles.input} placeholder="Correo" autoCapitalize="none"
        keyboardType="email-address" value={correo} onChangeText={setCorreo}
      />
      <TextInput
        style={styles.input} placeholder="Contraseña" secureTextEntry
        value={password} onChangeText={setPassword}
      />
      <TouchableOpacity style={styles.button} onPress={onSubmit} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Entrar</Text>}
      </TouchableOpacity>
      <Text style={styles.muted}>¿Olvidaste tu contraseña? Contacta al administrador.</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: "center", padding: 24, gap: 12, backgroundColor: "#f4f5f7" },
  brand: { fontSize: 26, fontWeight: "700", color: "#2d3748", textAlign: "center" },
  title: { fontSize: 18, textAlign: "center", marginBottom: 8, color: "#4a5568" },
  input: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#cbd5e0", borderRadius: 8, padding: 12, fontSize: 16 },
  button: { backgroundColor: "#2b6cb0", padding: 14, borderRadius: 8, alignItems: "center", marginTop: 4 },
  buttonText: { color: "#fff", fontWeight: "600", fontSize: 16 },
  error: { color: "#c53030", textAlign: "center" },
  muted: { color: "#718096", textAlign: "center", fontSize: 13, marginTop: 8 },
});
```

- [ ] **Step 4: Crear `seleccion-modulo.tsx` (RF-M04)**

```tsx
// mobile/src/app/seleccion-modulo.tsx
import { router } from "expo-router";
import { ScrollView, StyleSheet, Text, TouchableOpacity, View } from "react-native";

import { modulesForRole } from "@/lib/modules";
import { useAuth } from "@/store/auth";

export default function SeleccionModulo() {
  const user = useAuth((s) => s.user);
  const logout = useAuth((s) => s.logout);
  const modulos = user ? modulesForRole(user.rol.nombre_rol) : [];

  async function salir() {
    await logout();
    router.replace("/login");
  }

  return (
    <View style={styles.container}>
      <Text style={styles.hello}>Hola, {user?.nombre ?? ""}</Text>
      <Text style={styles.subtitle}>Selecciona un módulo</Text>
      <ScrollView contentContainerStyle={styles.grid}>
        {modulos.length === 0 && (
          <Text style={styles.muted}>Tu rol no tiene módulos móviles asignados.</Text>
        )}
        {modulos.map((m) => (
          <TouchableOpacity key={m.key} style={styles.card} onPress={() => router.push(m.ruta as any)}>
            <Text style={styles.cardText}>{m.label}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
      <TouchableOpacity style={styles.logout} onPress={salir}>
        <Text style={styles.logoutText}>Cerrar sesión</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24, backgroundColor: "#f4f5f7" },
  hello: { fontSize: 22, fontWeight: "700", color: "#2d3748", marginTop: 24 },
  subtitle: { fontSize: 16, color: "#4a5568", marginBottom: 16 },
  grid: { gap: 12 },
  card: { backgroundColor: "#2b6cb0", borderRadius: 12, padding: 28, alignItems: "center" },
  cardText: { color: "#fff", fontSize: 18, fontWeight: "600" },
  muted: { color: "#718096" },
  logout: { padding: 14, alignItems: "center" },
  logoutText: { color: "#c53030", fontWeight: "600" },
});
```

- [ ] **Step 5: Crear el placeholder `modulo/[key].tsx`**

```tsx
// mobile/src/app/modulo/[key].tsx
import { router, useLocalSearchParams } from "expo-router";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";

const LABELS: Record<string, string> = { mesero: "Mesero", caja: "Caja", cocina: "Cocina" };

export default function Modulo() {
  const { key } = useLocalSearchParams<{ key: string }>();
  const label = LABELS[key ?? ""] ?? "Módulo";
  return (
    <View style={styles.container}>
      <Text style={styles.title}>Módulo {label}</Text>
      <Text style={styles.muted}>Próximamente</Text>
      <TouchableOpacity style={styles.button} onPress={() => router.replace("/seleccion-modulo")}>
        <Text style={styles.buttonText}>Volver</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: "center", justifyContent: "center", gap: 12, backgroundColor: "#f4f5f7" },
  title: { fontSize: 24, fontWeight: "700", color: "#2d3748" },
  muted: { color: "#718096" },
  button: { backgroundColor: "#2b6cb0", paddingVertical: 12, paddingHorizontal: 24, borderRadius: 8, marginTop: 12 },
  buttonText: { color: "#fff", fontWeight: "600" },
});
```

- [ ] **Step 6: Borrar la pantalla demo**

```bash
rm mobile/src/app/explore.tsx
```

- [ ] **Step 7: Verificar tipos y que la suite sigue verde**

Run: `cd mobile && npx tsc --noEmit && npm test`
Expected: sin errores de tipos; 11 tests PASS.

- [ ] **Step 8: Verificación manual en Expo (web es lo más rápido)**

```bash
cd mobile && npx expo start --web
```
- Carga → redirige a login.
- Login con `admin@cafeteria.com` / `cambiar_en_local` → selección de módulo con las 3 tarjetas (Admin).
- Tocar un módulo → placeholder "Próximamente" → Volver.
- Cerrar sesión → vuelve a login.
- Reabrir (recargar) → entra directo a selección (sesión persistida).

> Para teléfono físico: poner la IP LAN en `mobile/.env` (`EXPO_PUBLIC_API_BASE_URL`) y `npx expo start`.

- [ ] **Step 9: Commit**

```bash
git add mobile/src/app
git commit -m "feat(mobile): navegacion, carga, login y seleccion de modulo"
```

---

## Cierre

- [ ] Push: `git push -u origin feature/mobile-auth`
- [ ] Abrir PR hacia `main`.

## Self-Review (cobertura del spec)

- Pantalla de carga (RF-M27/M28) → Task 4 (`index.tsx`). ✅
- Login (RF-M01) + sesión persistida (RF-M02) → Tasks 2,3 (session/store) + Task 4 (`login.tsx`). ✅
- Selección de módulo por rol (RF-M04) → Task 1 (`modules.ts`) + Task 4 (`seleccion-modulo.tsx`). ✅
- Rol→módulo con Admin=3 → Task 1. ✅
- secure-store + refresh-on-bootstrap → Tasks 2,3. ✅
- Cliente axios contra API → Task 2. ✅
- Config `EXPO_PUBLIC_API_BASE_URL` + nota IP LAN → Task 1. ✅
- Placeholder `modulo/[key]` (sin grupos) → Task 4. ✅
- Testing jest en lógica pura (client, store, modules) → Tasks 1,2,3. ✅
- RF-M03 (recuperar contraseña) solo como nota → Task 4 (`login.tsx`). ✅
- Eliminar demo del template → Task 4. ✅
