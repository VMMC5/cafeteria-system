# Rediseño "Cafetería Aroma" — login web, panel admin y app móvil

**Fecha:** 2026-08-10 · **Fuente de diseño:** carpetas `Cafetería Aroma loginn/` (Flask) y `Cafetería Aroma móvil/` (Expo) provistas por el usuario.

## Objetivo

Adoptar el sistema visual "Cafetería Aroma" de los mockups en el proyecto real:
tipografías **Lora** (títulos/cifras) y **Karla** (UI/cuerpo), paleta café
(`#33241B / #8A5A3B / #C89B6D / #F4EDE2`), tarjetas crema con bordes suaves,
logo con "vapor" animado, y componentes consistentes (chips, pills, badges,
steppers, barra inferior por rol en móvil).

## Alcance

### Web (Flask)
1. **Login** (`templates/auth/login.html` + CSS): adoptar el layout de dos
   paneles del mockup — panel de marca con imagen `cafeteria.png`, scrim,
   vapor animado y copy; tarjeta de formulario con validación cliente,
   toggle de contraseña y estados de carga/alerta.
   - Se conservan los contratos reales: campo `correo` (no `email`), POST
     clásico con flash + redirect (sin fetch/JSON), CSRF vía `csrf_token()`,
     y el enlace a soporte (`support_url`) en lugar de "¿Olvidaste tu
     contraseña?" (RF-M03 no implementado).
2. **Panel admin** (`base.html` + `app.css`): sidebar `coffee-950` con marca
   vapor + nav con dots + footer de usuario (avatar, correo, Salir); tokens
   nuevos de color/tipografía/radio/sombra; KPIs con cifra en Lora; pills,
   tabs, tablas, inputs y botones según `admin.css` del mockup. Se mantienen
   las clases existentes de las plantillas (restyle de valores, no renombre
   masivo) para minimizar el diff; el markup del sidebar sí se ajusta al
   mockup.
3. **Colores de Chart.js** del dashboard alineados a la paleta nueva.
4. **Fuentes vendorizadas** (woff2 locales, sin CDN — mismo criterio que
   Chart.js vendorizado).
5. **Tests**: se actualizan los asserts de markup/textos afectados
   (`test_web_ui.py`, y los que fijen clases/textos). Suite completa verde.

### Móvil (Expo)
1. **`src/theme/`**: tokens del mockup (`theme.js` → TypeScript): colores,
   fuentes, radios, spacing, tamaños, sombra de tarjeta.
2. **`src/ui/`**: componentes del mockup (`components.jsx` → TS):
   `NavIcon`, `BottomNav`, `Card`, `PrimaryButton`, `Chip`, `Input`,
   `Badge`, `Stepper`.
3. **Fuentes**: `@expo-google-fonts/lora` + `@expo-google-fonts/karla`
   cargadas en `_layout.tsx` (+ `react-native-svg` para iconos).
4. **Restyle de pantallas** con el theme: login, selección de módulo y los
   tres módulos (Mesero, Cocina, Caja). Pantallas raíz de cada módulo llevan
   `BottomNav` con los ítems del rol (mesero: Mesas/Pedidos/Salir; cocina:
   Pedidos/Recetas/Compras/Inventario/Salir; caja: Cobrar/Gastos/Salir);
   las subpantallas (menú, carrito, cobro, ajuste, compra-nueva,
   receta-detalle) conservan navegación de pila con header propio.
5. **Sin cambios de lógica**: stores, api, lib y navegación por rol quedan
   intactos; los 92 tests existentes y `tsc` deben seguir verdes.

## Fuera de alcance
- Backend (ningún cambio).
- Recuperar contraseña (RF-M03) — el mockup lo insinúa; no se implementa.
- Reestructurar navegación móvil a Tabs de expo-router (la barra se renderiza
  como componente en las pantallas raíz).
- Exportar/limpiar las carpetas de mockups (quedan como referencia).

## Criterios de éxito
- Web: 126+ tests verdes; login y panel visualmente fieles al mockup.
- Móvil: `tsc` limpio y 92 tests verdes; pantallas usan theme/componentes
  compartidos (sin colores azules `#2b6cb0` remanentes).
