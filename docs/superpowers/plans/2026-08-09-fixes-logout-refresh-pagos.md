# Fixes menores de seguridad y robustez — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cerrar tres pendientes chicos: `/logout` del panel web por POST (hoy vulnerable a logout-CSRF por GET), refresh-on-401 global en el móvil (hoy el token solo se renueva al arrancar la app), y el test de API de venta con pagos múltiples con excedente y referencia (último pendiente del PR #22).

**Architecture:** Logout: cambio de método + mini-form con CSRF en el sidebar (CSRFProtect global ya lo cubre). Móvil: lógica pura de decisión y single-flight en `lib/authRefresh.ts`, cableada como interceptor axios en un módulo nuevo `api/authInterceptor.ts` instalado desde `_layout.tsx` — ni las pantallas ni `store/auth.ts` cambian. API: solo un test nuevo.

**Tech Stack:** Flask + Flask-WTF (web), axios 1.x + zustand 5 + expo-router + jest-expo (móvil), FastAPI + pytest (backend).

**Spec:** `docs/superpowers/specs/2026-08-09-fixes-logout-refresh-pagos-design.md`

## Global Constraints

- **Un solo PR** con los tres fixes; rama `feat/fixes-logout-refresh-pagos`.
- `/logout` acepta **solo POST**; GET responde 405 (automático de Flask, sin handler especial).
- El botón de logout debe verse **idéntico** al enlace actual (icono + "Salir", mismos colores/hover).
- Móvil: máximo **un reintento** por petición; single-flight (N 401 concurrentes → 1 refresh); los 401 de `/auth/login` y `/auth/refresh` **nunca** disparan refresh.
- Al expirar de verdad (refresh falla): Alert único «Tu sesión expiró, inicia sesión de nuevo» + `router.replace("/login")`.
- **Las pantallas del móvil y `store/auth.ts` no se modifican** (solo `_layout.tsx` para instalar el interceptor).
- Comentarios, docstrings y mensajes de commit en español.
- Commits atómicos por tarea, con el test que la respalda.

## Cómo correr los tests

En el **checkout principal**: `docker compose exec api pytest -q` / `docker compose exec web pytest -q` / `cd mobile && npm test` / `npx tsc --noEmit`.

En un **worktree**, `docker compose exec` corre el código de `main` — usa contenedores efímeros (copia antes el `.env` del checkout principal; no omitas `--user`, deja archivos root):

```bash
docker run --rm --network cafeteria-system_default --user 1000:1000 \
  --env-file <worktree>/.env -v <worktree>/backend:/code -w /code \
  cafeteria-system-api pytest -q          # backend  (web: -v <worktree>/web:/code y la imagen cafeteria-system-web)
```

El móvil corre en el host: `cd <worktree>/mobile && npm install && npm test`. Copia también `mobile/.env` si vas a levantar Expo.

Baseline actual: backend **227**, web **123**, móvil **84** + `tsc` limpio.

---

## File Structure

**Backend** — Modificar: `backend/tests/test_ventas_api.py` (1 test nuevo; sin código de producción).

**Web** — Modificar: `web/app/auth/routes.py:47` (método), `web/app/templates/base.html:34-37` (form), `web/app/static/css/app.css:26-28` (botón), `web/tests/test_auth.py` (+2), `web/tests/test_csrf.py` (+1).

**Móvil**
- Crear `mobile/src/lib/authRefresh.ts` — decisión pura + single-flight. Crear `mobile/src/lib/authRefresh.test.ts`.
- Crear `mobile/src/api/authInterceptor.ts` — cableado: interceptor axios + store + navegación + Alert.
- Modificar `mobile/src/app/_layout.tsx` — instalar el interceptor.

---

## Task 1: Test de API — venta con pagos múltiples, excedente y referencia

Cierra el último pendiente del PR #22. Solo test: la funcionalidad ya existe y se validó a mano.

**Files:**
- Test: `backend/tests/test_ventas_api.py`

**Interfaces:**
- Consumes: helpers existentes `_pedido(client, db, admin_headers, numero, precio=116.0)` y `_metodo_id(db, nombre)` del mismo archivo.
- Produces: nada (tarea terminal).

- [ ] **Step 1: Escribir el test**

Añade al final de `backend/tests/test_ventas_api.py`:

```python
def test_cobrar_pago_dividido_excedente_y_referencia(
    client, db, admin_headers, cajero_headers
):
    """El caso del smoke manual del PR #22 que nunca tuvo test: pago dividido
    donde el Efectivo trae excedente (genera cambio) y la Tarjeta lleva
    referencia. La referencia debe persistir y el cambio ser suma − total."""
    pedido = _pedido(client, db, admin_headers, numero=606, precio=116.0)
    ef = _metodo_id(db, "Efectivo")
    ta = _metodo_id(db, "Tarjeta")
    r = client.post(
        "/api/v1/ventas",
        headers=cajero_headers,
        json={
            "id_pedido": pedido["id_pedido"],
            "pagos": [
                {"id_metodo_pago": ef, "monto": 150.0},
                {"id_metodo_pago": ta, "monto": 16.0, "referencia": "V-123"},
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert float(body["cambio"]) == 50.0  # 166 − 116
    assert len(body["pagos"]) == 2
    # Por método, no por índice: el orden de la relación no está garantizado.
    por_metodo = {p["id_metodo_pago"]: p for p in body["pagos"]}
    assert por_metodo[ta]["referencia"] == "V-123"
    assert por_metodo[ef]["referencia"] is None
    m = client.get(f"/api/v1/mesas/{pedido['id_mesa']}", headers=admin_headers).json()
    assert m["estado"] == "Disponible"
```

- [ ] **Step 2: Correrlo y verificar que pasa a la primera**

```bash
docker compose exec api pytest -q tests/test_ventas_api.py::test_cobrar_pago_dividido_excedente_y_referencia
```

Esperado: **1 passed**. Ojo: aquí no hay fase RED porque no hay código nuevo que hacer fallar — el test documenta comportamiento existente. Si **falla**, no "arregles" el test: eso significaría que la API no persiste la referencia o calcula mal el cambio, y es un bug real que hay que reportar antes de seguir.

- [ ] **Step 3: Correr la suite de ventas completa**

```bash
docker compose exec api pytest -q tests/test_ventas_api.py
```

Esperado: todos en verde (el archivo pasa de N a N+1).

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_ventas_api.py
git commit -m "test(api): venta con pago dividido, excedente en Efectivo y referencia

Cierra el último pendiente del PR #22: el caso validado solo con smoke manual
(Efectivo con cambio + Tarjeta con referencia) queda cubierto por la suite.
Los pagos se localizan por método, no por índice: el orden de la relación no
está garantizado."
```

---

## Task 2: `/logout` del panel web por POST

Elimina el logout-CSRF por GET. `CSRFProtect` global (PR #25) cubre el POST nuevo automáticamente.

**Files:**
- Modify: `web/app/auth/routes.py:47`
- Modify: `web/app/templates/base.html:34-37`
- Modify: `web/app/static/css/app.css:26-28`
- Test: `web/tests/test_auth.py`, `web/tests/test_csrf.py`

**Interfaces:**
- Consumes: `csrf_client`, `_token`, `_login`, `ADMIN_TOKENS`, `ADMIN_ME`, `USUARIOS` ya definidos en `web/tests/test_csrf.py`; `ADMIN_TOKENS`/`ADMIN_ME` en `web/tests/test_auth.py`.
- Produces: nada que otras tareas consuman.

- [ ] **Step 1: Escribir los tests que fallan — test_auth.py**

Añade al final de `web/tests/test_auth.py`:

```python
def _login_admin(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "secret123"})


def test_logout_por_post_cierra_sesion(client, monkeypatch):
    _login_admin(client, monkeypatch)
    r = client.post("/logout")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]
    # La sesión quedó cerrada: una página protegida vuelve a redirigir al login.
    r2 = client.get("/usuarios")
    assert r2.status_code == 302
    assert "/login" in r2.headers["Location"]


def test_logout_por_get_405(client, monkeypatch):
    """El logout por GET era vulnerable a CSRF (un <img src=/logout> cerraba la
    sesión del admin). La ruta ya solo acepta POST."""
    _login_admin(client, monkeypatch)
    r = client.get("/logout")
    assert r.status_code == 405
    # Y la sesión sigue viva: la página protegida carga (no redirige a login).
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: [])
    assert client.get("/usuarios").status_code == 200
```

- [ ] **Step 2: Escribir el test que falla — test_csrf.py**

Añade al final de `web/tests/test_csrf.py`:

```python
def test_logout_sin_token_es_rechazado(csrf_client, monkeypatch):
    """El form de logout vive en base.html (todas las páginas), no en una
    plantilla de módulo: merece su propio caso además del representativo."""
    _login(csrf_client, monkeypatch)
    r = csrf_client.post("/logout")
    assert r.status_code == 400
    # No cerró la sesión: la página protegida sigue cargando.
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: USUARIOS)
    assert csrf_client.get("/usuarios").status_code == 200
```

- [ ] **Step 3: Correr los tests y verificar que fallan**

```bash
docker compose exec web pytest -q \
  tests/test_auth.py::test_logout_por_post_cierra_sesion \
  tests/test_auth.py::test_logout_por_get_405 \
  tests/test_csrf.py::test_logout_sin_token_es_rechazado
```

Esperado: **3 failed** — hoy `POST /logout` da 405 (la ruta solo acepta GET), `GET /logout` da 302, y el POST sin token también 405 en vez de 400.

- [ ] **Step 4: Cambiar el método de la ruta**

En `web/app/auth/routes.py:47`:

```python
@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
```

- [ ] **Step 5: Convertir el enlace del sidebar en form**

En `web/app/templates/base.html:34-37`, reemplaza el `<a class="sidebar__logout">…</a>` por:

```html
      <form method="post" action="{{ url_for('auth.logout') }}" class="sidebar__logout-form">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <button type="submit" class="sidebar__logout" title="Cerrar sesión" aria-label="Salir">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="M16 17l5-5-5-5"/><path d="M21 12H9"/></svg>
          Salir
        </button>
      </form>
```

- [ ] **Step 6: Ajustar el CSS para que el botón se vea idéntico al enlace**

En `web/app/static/css/app.css:26-28`, reemplaza las reglas de `.sidebar__logout` por:

```css
.sidebar__logout-form { margin-left:auto; display:inline-flex; }
.sidebar__logout { display:inline-flex; align-items:center; gap:.35rem; color:#d9c9bb; font-size:.8rem; background:none; border:none; padding:0; font-family:inherit; cursor:pointer; }
.sidebar__logout:hover { color:#fff; }
.sidebar__logout svg { width:16px; height:16px; }
```

El `margin-left:auto` que empujaba el enlace a la derecha del flex `.sidebar__user` pasa al **form** (nuevo hijo directo del flex); el botón pierde los estilos de user-agent (`background`, `border`, `padding`, `font-family`) y conserva colores, gap y hover.

- [ ] **Step 7: Correr los tests y verificar que pasan**

```bash
docker compose exec web pytest -q \
  tests/test_auth.py::test_logout_por_post_cierra_sesion \
  tests/test_auth.py::test_logout_por_get_405 \
  tests/test_csrf.py::test_logout_sin_token_es_rechazado
```

Esperado: **3 passed.**

- [ ] **Step 8: Correr la suite web completa**

```bash
docker compose exec web pytest -q
```

Esperado: **126 passed** (123 + 3). Atención especial a `test_toda_plantilla_con_post_lleva_csrf_token` (debe seguir verde: el form nuevo lleva su token) y a `test_post_sin_token_anonimo_no_muestra_chrome_autenticado` (exige que "Salir" no aparezca en la página de rechazo anónima — el texto del botón sigue siendo "Salir", así que el assert sigue midiendo lo mismo).

- [ ] **Step 9: Commit**

```bash
git add web/app/auth/routes.py web/app/templates/base.html \
        web/app/static/css/app.css web/tests/test_auth.py web/tests/test_csrf.py
git commit -m "fix(web): logout solo por POST con token CSRF

Un <img src=/logout> en cualquier página cerraba la sesión del admin
(logout-CSRF): la ruta era GET y quedó fuera de la protección del PR #25,
que solo cubre POST. El enlace del sidebar pasa a ser un mini-form con
csrf_token y un botón estilizado idéntico; GET responde 405."
```

---

## Task 3: Móvil — lógica pura de refresh (`lib/authRefresh.ts`)

La decisión de cuándo refrescar y el single-flight, sin ninguna dependencia de axios/React/Expo — todo testeable con jest puro.

**Files:**
- Create: `mobile/src/lib/authRefresh.ts`
- Test: `mobile/src/lib/authRefresh.test.ts`

**Interfaces:**
- Consumes: nada.
- Produces (la Task 4 los importa desde `@/lib/authRefresh`):
  - `debeIntentarRefresh(status: number | undefined, url: string | undefined, esReintento: boolean): boolean`
  - `crearGestorRefresh<T>(refrescar: () => Promise<T>): { obtener: () => Promise<T> }`

- [ ] **Step 1: Escribir los tests que fallan**

Crea `mobile/src/lib/authRefresh.test.ts`:

```typescript
import { crearGestorRefresh, debeIntentarRefresh } from "./authRefresh";

test("debeIntentarRefresh: solo 401 de rutas normales sin reintento previo", () => {
  expect(debeIntentarRefresh(401, "/insumos", false)).toBe(true);
  expect(debeIntentarRefresh(401, "/pedidos/3/estado", false)).toBe(true);
});

test("debeIntentarRefresh: excluye auth, reintentos y otros errores", () => {
  expect(debeIntentarRefresh(401, "/auth/login", false)).toBe(false);
  expect(debeIntentarRefresh(401, "/auth/refresh", false)).toBe(false);
  expect(debeIntentarRefresh(401, "/insumos", true)).toBe(false);
  expect(debeIntentarRefresh(403, "/insumos", false)).toBe(false);
  expect(debeIntentarRefresh(500, "/insumos", false)).toBe(false);
  // Error de red: axios no trae response ni a veces config.
  expect(debeIntentarRefresh(undefined, "/insumos", false)).toBe(false);
  expect(debeIntentarRefresh(401, undefined, false)).toBe(false);
});

test("gestor: N llamadas concurrentes comparten un solo refresh", async () => {
  let llamadas = 0;
  let liberar!: (v: string) => void;
  const gestor = crearGestorRefresh(() => {
    llamadas += 1;
    return new Promise<string>((res) => (liberar = res));
  });
  const p1 = gestor.obtener();
  const p2 = gestor.obtener();
  liberar("token-nuevo");
  expect(await p1).toBe("token-nuevo");
  expect(await p2).toBe("token-nuevo");
  expect(llamadas).toBe(1);
});

test("gestor: al resolver se limpia y el siguiente 401 dispara un refresh nuevo", async () => {
  let llamadas = 0;
  const gestor = crearGestorRefresh(async () => {
    llamadas += 1;
    return `t${llamadas}`;
  });
  expect(await gestor.obtener()).toBe("t1");
  expect(await gestor.obtener()).toBe("t2");
  expect(llamadas).toBe(2);
});

test("gestor: el fallo también limpia y no deja promesa colgada", async () => {
  let llamadas = 0;
  const gestor = crearGestorRefresh(async () => {
    llamadas += 1;
    if (llamadas === 1) throw new Error("refresh caducado");
    return "recuperado";
  });
  await expect(gestor.obtener()).rejects.toThrow("refresh caducado");
  expect(await gestor.obtener()).toBe("recuperado");
});

test("gestor: los que esperaban un refresh fallido reciben el mismo fallo", async () => {
  let rechazar!: (e: Error) => void;
  const gestor = crearGestorRefresh(
    () => new Promise<string>((_res, rej) => (rechazar = rej))
  );
  const p1 = gestor.obtener().catch((e: Error) => e.message);
  const p2 = gestor.obtener().catch((e: Error) => e.message);
  rechazar(new Error("expirado"));
  expect(await p1).toBe("expirado");
  expect(await p2).toBe("expirado");
});
```

- [ ] **Step 2: Correr y verificar que falla**

```bash
cd mobile && npx jest src/lib/authRefresh.test.ts
```

Esperado: FAIL — `Cannot find module './authRefresh'`.

- [ ] **Step 3: Implementar el módulo**

Crea `mobile/src/lib/authRefresh.ts`:

```typescript
/**
 * Lógica pura del refresh-on-401 global. El cableado con axios, el store y la
 * navegación vive en api/authInterceptor.ts; aquí solo decisiones, para que
 * jest las cubra sin montar nada.
 */

const RUTAS_AUTH = ["/auth/login", "/auth/refresh"];

/**
 * ¿Este error amerita intentar un refresh? Solo un 401 de una ruta normal y
 * que no sea ya el reintento (un solo reintento por petición). Los 401 de
 * login/refresh son credenciales malas o refresh caducado: reintentarlos
 * ciclaría.
 */
export function debeIntentarRefresh(
  status: number | undefined,
  url: string | undefined,
  esReintento: boolean
): boolean {
  if (status !== 401 || esReintento || url === undefined) return false;
  return !RUTAS_AUTH.some((ruta) => url.includes(ruta));
}

/**
 * Single-flight: mientras haya un refresh en vuelo, todo el que lo pida
 * comparte la misma promesa (N pantallas con 401 simultáneo → 1 refresh).
 * Al resolverse o fallar se limpia, para que el siguiente 401 real dispare
 * un refresh nuevo.
 */
export function crearGestorRefresh<T>(refrescar: () => Promise<T>): {
  obtener: () => Promise<T>;
} {
  let enVuelo: Promise<T> | null = null;
  return {
    obtener() {
      if (enVuelo === null) {
        enVuelo = refrescar().finally(() => {
          enVuelo = null;
        });
      }
      return enVuelo;
    },
  };
}
```

- [ ] **Step 4: Correr y verificar que pasa**

```bash
cd mobile && npx jest src/lib/authRefresh.test.ts
```

Esperado: **6 passed.**

- [ ] **Step 5: Commit**

```bash
git add mobile/src/lib/authRefresh.ts mobile/src/lib/authRefresh.test.ts
git commit -m "feat(mobile): lógica pura del refresh-on-401 — decisión y single-flight

debeIntentarRefresh decide qué 401 ameritan refresh (excluye rutas de auth y
reintentos) y crearGestorRefresh garantiza que N 401 concurrentes compartan
un solo refresh. Sin dependencias: el cableado axios viene en la siguiente
tarea."
```

---

## Task 4: Móvil — interceptor cableado e instalación

El pegamento: interceptor de respuesta en `http`, renovación de tokens en store + SecureStore, reintento único, y expulsión al login con Alert cuando el refresh falla.

**Files:**
- Create: `mobile/src/api/authInterceptor.ts`
- Modify: `mobile/src/app/_layout.tsx`
- Test: no hay jest nuevo (la lógica decidible ya se probó en Task 3); verificación = `tsc` + suite completa + smoke manual del usuario.

**Interfaces:**
- Consumes: `debeIntentarRefresh` y `crearGestorRefresh` de `@/lib/authRefresh` (Task 3); `http` y `refresh` de `@/api/client`; `useAuth` de `@/store/auth`; `saveTokens`/`clearTokens` de `@/lib/session`.
- Produces: `instalarAuthInterceptor(): void` — idempotente; `_layout.tsx` la llama a nivel de módulo.

- [ ] **Step 1: Crear el interceptor**

Crea `mobile/src/api/authInterceptor.ts`:

```typescript
import { Alert } from "react-native";
import { router } from "expo-router";
import type { AxiosError, InternalAxiosRequestConfig } from "axios";

import { http, refresh, type Tokens } from "./client";
import { crearGestorRefresh, debeIntentarRefresh } from "../lib/authRefresh";
import { clearTokens, saveTokens } from "../lib/session";
import { useAuth } from "../store/auth";

/**
 * Refresh-on-401 global. Complementa (no reemplaza) el refresh del
 * bootstrap(): este cubre la expiración a media sesión, aquel el arranque en
 * frío. Las pantallas siguen pasando `access` como argumento; tras un refresh
 * el store ya tiene el token nuevo y el siguiente render lo toma — si una
 * pantalla alcanza a usar el viejo, este interceptor la vuelve a salvar.
 */

const gestor = crearGestorRefresh<Tokens>(() => {
  const rt = useAuth.getState().refreshToken;
  if (!rt) return Promise.reject(new Error("sin refresh token"));
  return refresh(rt);
});

async function renovarYReintentar(config: InternalAxiosRequestConfig) {
  const nt = await gestor.obtener();
  await saveTokens(nt.access_token, nt.refresh_token);
  useAuth.setState({ accessToken: nt.access_token, refreshToken: nt.refresh_token });
  (config as { _retry?: boolean })._retry = true;
  config.headers.Authorization = `Bearer ${nt.access_token}`;
  return http.request(config);
}

async function expulsarAlLogin() {
  // Solo avisa la primera vez: tras poner "noauth", los 401 rezagados de
  // llamadas concurrentes ya no encuentran una sesión que expirar.
  const habiaSesion = useAuth.getState().status === "auth";
  await clearTokens();
  useAuth.setState({
    status: "noauth",
    user: null,
    accessToken: null,
    refreshToken: null,
  });
  if (habiaSesion) {
    router.replace("/login" as any);
    Alert.alert("Sesión expirada", "Tu sesión expiró, inicia sesión de nuevo.");
  }
}

let instalado = false;

/** Registra el interceptor una sola vez (idempotente ante re-renders/HMR). */
export function instalarAuthInterceptor(): void {
  if (instalado) return;
  instalado = true;
  http.interceptors.response.use(undefined, async (error: AxiosError) => {
    const config = error.config;
    const esReintento = Boolean((config as { _retry?: boolean } | undefined)?._retry);
    if (
      config === undefined ||
      !debeIntentarRefresh(error.response?.status, config.url, esReintento)
    ) {
      throw error;
    }
    try {
      return await renovarYReintentar(config);
    } catch {
      await expulsarAlLogin();
      throw error;
    }
  });
}
```

- [ ] **Step 2: Instalarlo en el layout raíz**

En `mobile/src/app/_layout.tsx`, añade el import y la llamada a nivel de módulo (antes del componente):

```typescript
import { Stack } from "expo-router";

import { instalarAuthInterceptor } from "@/api/authInterceptor";

instalarAuthInterceptor();
```

El resto del archivo no cambia.

- [ ] **Step 3: Verificar tipos y que nada se rompió**

```bash
cd mobile && npx tsc --noEmit && npm test
```

Esperado: `tsc` sin salida; **90 passed** (84 + 6 de la Task 3), 0 failed. Atención a `store/auth.test.ts`: no debe verse afectado (el store no cambió; el interceptor no se importa en sus tests).

- [ ] **Step 4: Verificación funcional mínima del cableado**

El reintento HTTP real se prueba en el smoke manual del usuario (spec §Verificación). Aquí solo confirma que la app arranca con el interceptor instalado:

```bash
cd mobile && npx expo start
```

Abre la app (o el bundle web con `w`), inicia sesión y navega a cualquier módulo. Esperado: comportamiento idéntico al actual (el interceptor no interfiere con respuestas 2xx ni con errores no-401).

- [ ] **Step 5: Commit**

```bash
git add mobile/src/api/authInterceptor.ts mobile/src/app/_layout.tsx
git commit -m "feat(mobile): refresh-on-401 global con reintento único y expulsión al login

Interceptor de respuesta en http: un 401 de ruta normal dispara un refresh
single-flight, renueva tokens en store + SecureStore y reintenta la petición
una vez. Si el refresh falla, limpia la sesión, avisa una sola vez y devuelve
al login con router.replace. bootstrap() y las pantallas quedan intactos."
```

---

## Task 5: Documentación

**Files:**
- Modify: `progress.md` — quitar de deuda «falta test de API para venta con pagos múltiples» (línea compartida con la paginación de reportes: recorta solo esa mitad) y «Sin refresh-on-401 global en el móvil»; registrar los tres fixes en "Próximo" como rama lista para PR (sin inventar número de PR).
- Modify: `CONTEXTO-PROYECTO.md` — actualizar la limitación de refresh-on-401 y el conteo de tests si la sección lo trae.

**Interfaces:** ninguna.

- [ ] **Step 1: Actualizar los dos archivos según lo anterior**

- [ ] **Step 2: Verificar que no queda referencia a los pendientes cerrados**

```bash
grep -rn "refresh-on-401\|pagos múltiples\|logout" progress.md CONTEXTO-PROYECTO.md
```

Esperado: solo menciones históricas o del slice nuevo; ninguna que los liste como pendientes.

- [ ] **Step 3: Commit**

```bash
git add progress.md CONTEXTO-PROYECTO.md
git commit -m "docs: registra el slice de fixes menores — logout POST, refresh-on-401, test de pagos múltiples"
```

---

## Verificación final antes del PR

- [ ] Suites completas: backend **228** · web **126** · móvil **90** + `tsc` limpio.
- [ ] Verificación manual del usuario (spec §Verificación manual):
  1. Panel: cerrar sesión desde el sidebar (idéntico visualmente); `/logout` por URL directa → 405 y la sesión sigue viva.
  2. Móvil: con el access token expirado (acortar TTL en `.env` si hace falta), cualquier acción se completa sola tras el refresh transparente.
  3. Móvil: con ambos tokens inválidos, la siguiente acción muestra el Alert y devuelve al login.
