# Diseño — Rediseño del panel web ("Cafetería Aroma")

**Fecha:** 2026-07-06
**Tipo:** Rediseño visual del panel web admin (Flask). Solo plantillas + CSS (+ un filtro de presentación en la ruta de usuarios). **Sin cambios de API/backend, sin migraciones.**
**Marca:** "Cafetería Aroma" (login) · "Café Admin" (sidebar).

---

## Objetivo

Adoptar la identidad visual de las mockups ("Cafetería Aroma", tema café con sidebar)
y rediseñar las páginas que **ya existen** — login, Estadísticas (el dashboard actual del
Slice A) y Usuarios (lista + formulario) — manteniendo datos reales y el patrón de cliente
delgado. Las páginas nuevas del mockup (Reportes con export, analítica avanzada) se
construyen con este mismo diseño en su propio slice.

## Decisiones tomadas

- **Alcance:** rediseñar solo lo existente ahora; diferir Reportes (Slice B) y los widgets
  analíticos avanzados.
- **Marca:** "Cafetería Aroma" / "Café Admin" literal, con ícono de taza (SVG inline).
- **Navegación:** el "Dashboard" actual se renombra a **"Estadísticas"** en la UI. Sidebar:
  Estadísticas + Usuarios y Roles. (La ruta interna sigue siendo `/dashboard` /
  `dashboard.index` para no romper el Slice A; solo cambia la etiqueta y el encabezado.)
- **Formulario de usuario:** se mantienen los **campos reales del backend** (`nombre`,
  `apellido_paterno`, `apellido_materno`, `correo`, `nombre_usuario`, `password`). **No** se
  agrega `teléfono` (la API no lo soporta).
- **Sin dependencias externas:** el web no tiene bundler ni CDN garantizado; el tema usa
  fuentes del sistema (no se cargan web fonts).

---

## Sección 1 — Sistema de diseño (tokens en `app.css`)

Variables en `:root`:
- **Paleta:** fondo crema `#f0ebe4`; superficie `#ffffff`; sidebar café oscuro `#3a2a20`;
  texto `#2c1e16`; acento ámbar `#c8862f`; ganancia (verde) `#2f7d4f`; gasto (rojo)
  `#c0483b`; bordes suaves `#e7ddd3`.
- **Badges de rol:** Administrador = morado (`#ede9fe`/`#5b21b6`), Cajero = café
  (`#efe6da`/`#6b4423`), Cocinero = verde (`#d8efdd`/`#1f6b3a`), Mesero = ámbar
  (`#f6e6c9`/`#8a5a12`).
- **Tipografía (stacks del sistema):** títulos/marca `Georgia, 'Times New Roman', serif`;
  cuerpo `system-ui, -apple-system, sans-serif`; números/tablas `ui-monospace,
  'SFMono-Regular', monospace`.
- **Tarjetas:** `border-radius` 12px, sombra suave, header de sección en serif.

*Mejora opcional (no en este slice):* vendorizar Playfair Display localmente para el match
tipográfico exacto.

## Sección 2 — App shell (`base.html`)

- **Sidebar fija** (café oscuro, ~230px): marca "☕ Café **Admin**"; ítems de nav con ícono
  SVG inline — **Estadísticas** (`dashboard.index`), **Usuarios y Roles**
  (`usuarios.listar`). El ítem activo se resalta con fondo ámbar tenue y borde. (Reportes se
  añade en el Slice B.)
- **Footer de usuario:** avatar circular con iniciales de `current_user.nombre`, nombre y
  rol.
- **Main:** fondo crema, contenedor con header de página (título serif + subtítulo) y slot
  para botón de acción a la derecha.
- **Responsive:** bajo ~768px la sidebar se colapsa a una barra superior con botón toggle
  (CSS + un checkbox/`<details>` o mínimo JS).
- **Flash messages** se re-estilizan dentro del main.
- El **login usa un layout propio** (no hereda el shell con sidebar): se separa mediante un
  bloque/base distinto (p. ej. `base_auth.html` o un `{% block fullpage %}`), de modo que la
  página de login no muestre navegación.

## Sección 3 — Páginas

### Login (`auth/login.html`)
Split de dos columnas:
- Izquierda: panel café oscuro, ilustración de taza (SVG inline), "Cafetería **Aroma**",
  subtítulo "Panel de Administración General".
- Derecha: tarjeta con "Iniciar sesión", "Acceso exclusivo para administradores", campos
  correo/contraseña, botón "Ingresar", y enlace de soporte (`support_url`).
- Responsive: se apila en móvil (tarjeta arriba).

### Estadísticas (`dashboard/index.html`, restyle)
Las **mismas** unidades del Slice A, re-estilizadas:
- 6 tarjetas KPI (etiqueta en mayúsculas + valor grande; utilidad con acento).
- Selector de periodo como "pills" (Hoy / 7 días / Este mes / Rango) + inputs de fecha.
- Gráfica de línea (ventas/día) y de barras (top productos) en tarjetas con header serif.
- Encabezado de página "Estadísticas".
- **No** se agregan dona, % vs mes anterior, nivel de inventario ni tendencia diaria
  (diferidos, requieren endpoints nuevos).

### Usuarios y Roles (`usuarios/list.html`)
- Header "Usuarios y Roles" + contador "N usuarios registrados" + botón "+ Nuevo usuario".
- Buscador (parámetro `q`, ya soportado por la API).
- Filtros **Rol** y **Estado** como `<select>` GET, aplicados **en la ruta Flask** sobre la
  lista devuelta por la API (filtrado de presentación; no requiere endpoint nuevo).
- Tabla: avatar de iniciales, nombre + correo apilados, **badge de rol** de color, punto de
  estado (Activo/Inactivo), acciones (editar + desactivar) como íconos.

### Nuevo/Editar usuario (`usuarios/form.html`)
- Dos columnas.
- Izquierda "Datos del usuario": los campos reales del backend (arriba), con el checkbox
  "Mostrar contraseña" existente.
- Derecha "Asignar rol": **tarjetas de radio** para cada rol (`id_rol`), y panel **"Permisos
  del rol"** informativo — descripción estática por rol mostrada vía JS según el radio
  seleccionado. Es **decorativo/informativo**; el backend no modela permisos granulares.

## Sección 4 — Arquitectura, datos y testing

- **Arquitectura:** cambio solo de presentación. Plantillas Jinja + `app.css`. La única
  lógica nueva es el filtrado de la lista de usuarios por Rol/Estado en la ruta
  `usuarios.listar` (sobre datos ya devueltos por la API). Se preserva el patrón cliente
  delgado (todo dato viene de la API vía `api_gateway.call`).
- **Datos:** sin endpoints nuevos. La página Estadísticas consume los mismos
  `reportes/{resumen,ventas-por-dia,top-productos}` del Slice A.
- **Testing (pytest web):**
  - Los tests existentes siguen verdes (login 200; `/dashboard` con KPIs y "Utilidad";
    lista y form de usuarios). Se ajustan solo asserts que dependan de texto cambiado.
  - Nuevos: sidebar presente en páginas autenticadas (marca "Café Admin", enlaces
    Estadísticas/Usuarios); login con nuevo layout (marca "Cafetería Aroma", "Acceso
    exclusivo"); badge de rol en la lista; el filtro Rol/Estado acota la lista.
- **Verificación:** reiniciar el contenedor `web` tras los cambios (cambios de plantilla/
  registro no se recargan en caliente) y smoke check de las 4 pantallas.
- **Entrega:** rama y PR propios (`feature/web-redesign`), slice de UI independiente del
  Slice B. Sin migraciones.

## Fuera de alcance (YAGNI — van en su slice, con este mismo diseño)

- Página **Reportes** + export PDF/XLSX (Slice B).
- Widgets analíticos avanzados: dona de productos, KPIs con % vs mes anterior, nivel de
  inventario, tendencia de pedidos diarios (requieren endpoints nuevos).
- Campo `teléfono` en usuarios (requiere cambio de backend).
- Modelo de permisos por rol editable (el panel de permisos es informativo).
- Web fonts externas (Playfair Display) salvo que se vendoricen.
