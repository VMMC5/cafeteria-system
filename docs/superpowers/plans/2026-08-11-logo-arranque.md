# Logo en el arranque — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mostrar el logo oficial (PNG ya copiado en `mobile/assets/images/logo-aroma.png`) en el splash nativo, la pantalla de carga y el ícono de la app.

**Architecture:** Solo config (`app.json`) + un `<Image>` en `index.tsx`. Sin lógica nueva ni tests nuevos — el gate es config válida + suites existentes.

**Tech Stack:** Expo SDK 57 (`expo-splash-screen` plugin), React Native.

**Spec:** `docs/superpowers/specs/2026-08-11-logo-arranque-design.md`

## Global Constraints

- El asset `mobile/assets/images/logo-aroma.png` **ya existe** (2048×2048); no se re-copia ni se renombra.
- Colores exactos: splash y fondo adaptativo `#FEF8EA` (muestreado del PNG).
- Idioma: comentarios y commit en español.

## File Structure

```
mobile/app.json               (edit)  icon, adaptiveIcon, plugin expo-splash-screen
mobile/src/app/index.tsx      (edit)  <Image> del logo en la vista de carga
mobile/assets/images/logo-aroma.png   (ya en el árbol, se incluye en el commit)
```

---

## Tarea 1 — Config de Expo y pantalla de carga

**Files:**
- Modify: `mobile/app.json`, `mobile/src/app/index.tsx`
- Add (ya presente en el working tree): `mobile/assets/images/logo-aroma.png`

- [ ] **Paso 1: `app.json`**

En `expo`: `"icon": "./assets/images/logo-aroma.png"`. Eliminar el bloque `"ios": { "icon": "./assets/expo.icon" }` completo (iOS cae al `icon` raíz). En `android.adaptiveIcon` dejar exactamente:

```json
      "adaptiveIcon": {
        "backgroundColor": "#FEF8EA",
        "foregroundImage": "./assets/images/logo-aroma.png"
      },
```

En el plugin `expo-splash-screen` dejar exactamente:

```json
      [
        "expo-splash-screen",
        {
          "backgroundColor": "#FEF8EA",
          "image": "./assets/images/logo-aroma.png",
          "imageWidth": 200
        }
      ],
```

- [ ] **Paso 2: `src/app/index.tsx`**

Añadir `Image` al import de `react-native` (queda `ActivityIndicator, Image, StyleSheet, Text, View`). En la vista de `status === "loading"`, arriba del `<Text style={styles.brand}>`:

```tsx
        <Image
          source={require("../../assets/images/logo-aroma.png")}
          style={styles.logo}
        />
```

y en los estilos:

```ts
  logo: { width: 160, height: 160 },
```

- [ ] **Paso 3: Verificación**

```bash
cd /home/vikca/cafeteria-system/.claude/worktrees/logo-splash/mobile
npm install            # primera vez en el worktree
npx expo config --type public > /dev/null && echo "CONFIG OK"
npm test && npx tsc --noEmit
```

Esperado: CONFIG OK, 113 tests verdes, tsc limpio.

- [ ] **Paso 4: Commit**

```bash
git add mobile/app.json mobile/src/app/index.tsx mobile/assets/images/logo-aroma.png
git commit -m "feat(mobile): logo oficial en splash, pantalla de carga e ícono de la app"
```

## Tarea 2 — Docs y push

- [ ] `progress.md` en la rama: bullet corto en la sección de Completado (nuevo `### Post-Sprint 6 — Logo en el arranque del móvil` antes de `### Cobertura de tests`): logo oficial en splash nativo (`#FEF8EA` muestreado del arte), pantalla de carga e ícono adaptativo; assets del template de Expo fuera del arranque; recordatorio de que el ícono del launcher requiere build nativo (Expo Go no lo muestra). Los conteos de tests no cambian.
- [ ] Commit (`docs: progress.md — logo en el arranque del móvil`) y push de la rama.
