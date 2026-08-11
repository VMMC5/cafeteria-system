# APK instalable vía EAS Build — Diseño

**Fecha:** 2026-08-11 · **Rama:** `feature/eas-apk` · **Estado:** aprobado por el usuario

## Problema

La app móvil solo corre en Expo Go (desarrollo). Se quiere un **APK instalable**
en cualquier teléfono Android de la red local, con el ícono/splash del logo
oficial (que Expo Go no muestra) y apuntando a la API del stack Docker en la PC.

## Decisiones del usuario

- **EAS Build en la nube** (cuenta gratis de Expo); no se instala Android SDK local.
- La API horneada en el binario es la **IP LAN actual**:
  `http://10.134.78.227:8000/api/v1`. Si la IP cambia, se recompila —
  hacer la URL configurable desde la app queda fuera de alcance.

## Diseño

- **`app.json`:**
  - `"name"` pasa de `"mobile"` a `"Cafetería Aroma"` (nombre visible bajo el
    ícono al instalar); `slug` se queda en `"mobile"`.
  - `android.package: "com.cafeteriaaroma.app"` (identificador requerido por el
    build nativo).
  - Plugin **`expo-build-properties`** (dependencia nueva, instalada con
    `npx expo install` para alinear versión al SDK 57) con
    `android.usesCleartextTraffic: true` — sin esto, los builds release de
    Android bloquean el tráfico `http://` en claro y el APK instalaría pero
    jamás conectaría con la API LAN.
- **`eas.json` nuevo** (raíz de `mobile/`):
  - `cli.appVersionSource: "remote"` (evita prompts de versión).
  - Perfil `build.preview`: `distribution: "internal"`,
    `android.buildType: "apk"`, y
    `env.EXPO_PUBLIC_API_BASE_URL = "http://10.134.78.227:8000/api/v1"` —
    horneada en el perfil porque `mobile/.env` no viaja al build.
- **Pasos interactivos del usuario** (credenciales, fuera del repo):
  1. Cuenta gratis en expo.dev + `npx eas login` (desde `mobile/` del worktree).
  2. `npx eas build --platform android --profile preview` — la primera vez
     pregunta si crea el proyecto EAS (escribe `extra.eas.projectId` en
     `app.json` → se commitea después como chore) y si genera el **keystore**
     (sí; queda resguardado en la cuenta de Expo).
  3. Descargar el APK del link que da EAS e instalarlo (permitir orígenes
     desconocidos).

## Fuera de alcance

- Builds de iOS, AAB de Play Store, canales de updates OTA (`eas update`).
- URL de API configurable en runtime.

## Criterios de éxito

- `npx expo config --type public` resuelve sin error con el plugin nuevo.
- `npm test` verde y `npx tsc --noEmit` limpio.
- El usuario obtiene un APK que instala, muestra ícono y splash con el logo, y
  opera contra la API del stack local (login y flujo básico).
