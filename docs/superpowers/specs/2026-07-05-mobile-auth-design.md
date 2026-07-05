# Diseño — App móvil: carga, login y selección de módulo (feature/mobile-auth)

**Fecha:** 2026-07-05
**Sprint:** 1 (slice móvil)
**Rama:** `feature/mobile-auth`

## Objetivo

Que la app móvil (React Native + Expo) arranque con una pantalla de carga, permita
iniciar sesión contra la API con sesión persistida, y muestre una pantalla de
selección de módulo según el rol del usuario. Los módulos (Mesero/Caja/Cocina)
llevan a pantallas placeholder; su contenido real es Sprint 2+.

Cubre: RF-M01, RF-M02, RF-M04, RF-M27, RF-M28.

## Decisiones tomadas (brainstorming)

1. **Alcance:** carga + login + selección de módulo (módulos = placeholders).
2. **Rol→módulo:** Mesero→Mesero, Cajero→Caja, Cocinero→Cocina; **Administrador→los 3**.
   La pantalla muestra solo los módulos permitidos por el rol.
3. **Sesión:** zustand + `expo-secure-store`; refresh-on-bootstrap.
4. **URL de API:** `EXPO_PUBLIC_API_BASE_URL`; IP LAN para dispositivo físico.
5. **Testing:** `jest-expo` sobre lógica pura (client, store, mapeo rol→módulo).

## Navegación (expo-router)

Se reemplaza el layout de tabs del template por un Stack. Estructura final:

```
src/app/
├── _layout.tsx           # Providers + Stack; monta el store
├── index.tsx             # Pantalla de carga (RF-M27/28): bootstrap + redirección
├── login.tsx             # Login (RF-M01/M02)
├── seleccion-modulo.tsx  # Selección de módulo (RF-M04) + logout
└── modulo/[key].tsx      # Placeholder de módulo (mesero|caja|cocina)
```

**Nota de routing:** se usa una ruta dinámica `modulo/[key].tsx` en vez de grupos
`(mesero)/`, `(caja)/`, `(cocina)/` porque las carpetas con paréntesis de expo-router
son *grupos* que no añaden segmento a la URL y colisionarían con `/` (index). Los
grupos por rol con sus pantallas reales llegan en Sprint 2+.

Se eliminan las pantallas demo del template (`explore.tsx`, componentes de ejemplo
no usados). El `index.tsx` de ejemplo se reemplaza por la pantalla de carga.

## Componentes de lógica

### `src/lib/session.ts` — persistencia
Envoltorio de `expo-secure-store`:
- `saveTokens(access, refresh)`, `loadTokens() -> {access, refresh} | null`,
  `clearTokens()`.

### `src/api/client.ts` — cliente HTTP
Instancia axios con `baseURL = process.env.EXPO_PUBLIC_API_BASE_URL`:
- `login(correo, password) -> {access_token, refresh_token}` (POST form a `/auth/login`).
- `getMe(access) -> Usuario` (GET `/auth/me` con Bearer).
- `refresh(refreshToken) -> {access_token, refresh_token}` (POST `/auth/refresh`).
Lanza el error de axios; las capas superiores lo traducen a mensajes.

### `src/store/auth.ts` — estado (zustand)
Estado: `{ status: "loading" | "auth" | "noauth", user, accessToken, refreshToken }`.
Acciones:
- `bootstrap()`: carga tokens de secure-store; si hay, valida con `getMe`; si el
  access falla, intenta `refresh` y reintenta `getMe`; éxito → `status="auth"`,
  guarda user+tokens; fallo → `clearTokens()`, `status="noauth"`.
- `login(correo, password)`: `client.login` → `saveTokens` → `getMe` → `status="auth"`.
- `logout()`: `clearTokens()` → estado limpio, `status="noauth"`.

### `src/lib/modules.ts` — mapeo rol→módulo
```ts
type Modulo = { key: "mesero" | "caja" | "cocina"; label: string; ruta: string };
modulesForRole(rol: string): Modulo[]
```
- Mesero → [Mesero]; Cajero → [Caja]; Cocinero → [Cocina];
  Administrador → [Mesero, Caja, Cocina]; otro → [].
- `ruta` de cada módulo es `/modulo/<key>` (ej. `/modulo/mesero`).

## Pantallas

- **`index.tsx` (carga, RF-M27/M28):** al montar llama `bootstrap()`. Mientras
  `status==="loading"` muestra logo + indicador. Al resolver: `Redirect` a
  `/login` (noauth) o `/seleccion-modulo` (auth).
- **`login.tsx` (RF-M01/M02):** campos correo + contraseña; botón entrar; muestra
  error si las credenciales fallan; enlace "¿Olvidaste tu contraseña? Contacta al
  administrador" (RF-M03 diferido, solo nota). Éxito → redirige a selección.
- **`seleccion-modulo.tsx` (RF-M04):** saluda al usuario; renderiza tarjetas de
  `modulesForRole(user.rol.nombre_rol)`; tocar una navega a su ruta; botón salir.
- **Placeholders de módulo:** título "Módulo X (próximamente)" + botón volver a
  selección.

## Configuración de URL de la API

- `mobile/.env` con `EXPO_PUBLIC_API_BASE_URL`. Expo inyecta variables con prefijo
  `EXPO_PUBLIC_` en `process.env` durante el bundling.
- `mobile/.env.example` con el placeholder y la nota:
  - Emulador Android: `http://10.0.2.2:8000/api/v1`.
  - Dispositivo físico (Expo Go): IP LAN del PC, ej. `http://192.168.1.X:8000/api/v1`.
  - Web (`npm run web`): `http://localhost:8000/api/v1`.
- `.env` del móvil se ignora en git (ya cubierto por el `.gitignore` de Node).

## Manejo de errores

| Situación | Comportamiento |
|---|---|
| Credenciales inválidas en login | Mensaje "correo o contraseña incorrectos" |
| Sin red / API caída | Mensaje "no se pudo conectar con el servidor" |
| Token expirado al arrancar | Intenta refresh; si falla, va a login |
| Rol sin módulos | Mensaje "tu rol no tiene módulos móviles asignados" |

## Testing (`jest-expo`, lógica pura)

Configurar `jest-expo` + script `test`. Casos:
- `modules.test.ts`: `modulesForRole` devuelve el módulo correcto por rol; Admin los
  3; rol desconocido vacío.
- `client.test.ts`: `login` postea el form correcto y devuelve tokens; `getMe` manda
  Bearer (axios mockeado).
- `auth.store.test.ts`: `login` guarda tokens y pone `status="auth"`; `logout`
  limpia; `bootstrap` sin tokens → `noauth` (secure-store y client mockeados).

Las pantallas se verifican manualmente con `npx expo start` / `npm run web`.

## Fuera de alcance (YAGNI)

Recuperación de contraseña real (RF-M03, solo nota), contenido real de los módulos
(Sprint 2+), notificaciones push, interceptor global de refresh-on-401 (el bootstrap
cubre la expiración al arrancar; se añadirá cuando haya llamadas de datos), tema
oscuro personalizado.
