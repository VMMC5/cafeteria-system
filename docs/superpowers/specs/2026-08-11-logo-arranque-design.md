# Logo en el arranque de la app móvil — Diseño

**Fecha:** 2026-08-11 · **Rama:** `feature/logo-splash` · **Estado:** aprobado por el usuario

## Problema

El arranque de la app conserva los assets del template de Expo: splash nativo azul
(`#208AEF`) con ícono genérico, ícono de launcher del template y pantalla de carga
solo con texto. El usuario proporcionó el logo oficial (taza azul + monograma "A"
caramelo sobre card crema, PNG 2048×2048) y quiere verlo al iniciar la app.

## Decisiones del usuario

- El logo aparece en: **splash nativo**, **pantalla de carga** (`index.tsx`) y
  **ícono de la app** (launcher).
- Se usa el **PNG original** (no una recreación SVG). Fuente de verdad:
  `mobile/assets/images/logo-aroma.png`.
- La taza azul introduce un color fuera de la paleta café/caramelo del tema: es
  intencional del arte elegido.

## Diseño

- **Colores muestreados del PNG:** fondo exterior `#FEF8EA` (esquinas), card
  interior `#FBF4E1`. El splash usa `#FEF8EA` para que el arte se funda con el
  fondo sin mostrar un recorte.
- **Splash nativo** (`app.json`, plugin `expo-splash-screen`): `image` →
  `./assets/images/logo-aroma.png`, `backgroundColor` → `#FEF8EA`,
  `imageWidth` → `200`.
- **Ícono de la app** (`app.json`): `icon` raíz → `logo-aroma.png`. Android
  adaptativo: `foregroundImage` → `logo-aroma.png` (el arte trae márgenes que
  sobreviven el recorte), `backgroundColor` → `#FEF8EA`, y se **eliminan**
  `backgroundImage` y `monochromeImage` (eran arte del template de Expo; sin
  monochrome el ícono temático simplemente no se ofrece — mejor que mostrar el
  logo de Expo). Se elimina también el override `ios.icon` (bundle `.icon` del
  template) para que iOS caiga al `icon` raíz.
- **Pantalla de carga** (`src/app/index.tsx`): `<Image>` del logo (160×160)
  arriba del texto «Cafetería Aroma» y el spinner, que se conservan.

## Fuera de alcance

- Favicon del target web de Expo y assets muertos del template (react-logo,
  expo-badge…): no se tocan.
- Ninguna lógica ni pantalla más allá de `index.tsx`.

## Criterios de éxito

- `npx expo config --type public` resuelve sin error (config válida).
- `npm test` verde y `npx tsc --noEmit` limpio.
- Verificación visual del usuario en dispositivo: splash con el logo sobre fondo
  crema al abrir, logo en la pantalla de carga. El ícono del launcher solo cambia
  en un build nativo (Expo Go no lo refleja) — queda documentado.
