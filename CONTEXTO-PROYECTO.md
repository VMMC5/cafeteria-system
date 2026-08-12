# Contexto del Proyecto — Cafeteria-System

> Documento de contexto integral para retomar el proyecto en cualquier sesión (humana o con IA).
> **Generado:** 2026-08-04 · **Actualizado:** 2026-08-11 · **Repo:** [VMMC5/cafeteria-system](https://github.com/VMMC5/cafeteria-system) · **Rama principal:** `main`

---

## 1. ¿Qué es?

Sistema integral de gestión para una cafetería ("Cafetería Aroma"): automatiza **pedidos, cocina, cobro, inventario, compras, gastos y reportes**. Consta de tres aplicaciones que comparten una sola API:

| Componente | Tecnología | Rol |
|---|---|---|
| `backend/` | **Python + FastAPI** + SQLAlchemy + Alembic | API REST (fuente única de verdad, JWT) |
| `web/` | **Flask** + Jinja2 + Chart.js (vendorizado) | Panel de administración (admin-only): usuarios, dashboard, estadísticas, reportes BI con export PDF/XLSX |
| `mobile/` | **React Native + Expo** (expo-router, TypeScript) | App operativa por rol: Mesero, Cocina, Caja |
| BD | **PostgreSQL 16** | 23 tablas (3 migraciones Alembic + seeds) |
| Infra | **Docker Compose** | Servicios: `db`, `api` (:8000), `web` (:5000), `adminer` (:8080). El móvil corre fuera de Docker con Expo. |

**Metodología:** cada slice pasa por brainstorming → spec → plan → implementación TDD → PR. Los specs y planes viven en `docs/superpowers/specs/` y `docs/superpowers/plans/` (21 planes, 20 specs).

---

## 2. Estado actual (agosto 2026)

- **Sprints 0–6 completos y mergeados a `main`** (PRs #1–#19) + **PR #20** (fix de importes en móvil) + **PR #21** (módulo Catálogo en el panel web) + **PR #22** (pago dividido en Caja móvil) + **PR #23** (recetas en Cocina móvil) + **PR #24** (guard de mesa Ocupada en la API) + **PR #25** (protección CSRF en el panel web) + **PR #26** (inventario y kárdex a 3 decimales, squash `84d8161`; incluye el fix de `seed_base` sobre BD vacía).
- **PR #27 mergeado (squash `b1f0e80`):** tres fixes menores — test de API para venta con pagos múltiples (cierra el último pendiente del PR #22), `/logout` del panel web de GET a POST (cerraba una vulnerabilidad de logout-CSRF que quedó fuera del alcance del PR #25) y refresh-on-401 global en el móvil (interceptor de axios con single-flight, `lib/authRefresh.ts` + `api/authInterceptor.ts`).
- **PR #29 mergeado (squash `3f479bc`): rediseño "Cafetería Aroma" en web y móvil.** Login web de dos paneles + panel admin restyleado (Lora/Karla vendorizadas, iconos SVG inline en el sidebar); móvil con `src/theme/` + `src/ui/` (BottomNav por rol, Badge, Chip, Stepper…), fuentes Google + `react-native-svg` + `expo-print`. Extras funcionales de la revisión visual: comprobante completo con botón **Imprimir Ticket**, detalle de compra en Cocina, unidades en Nueva compra, confirmación de logout, y temporizador con urgencia en Cocina (⚠️ umbrales en modo demo: 1/2 min — `RETRASO_*` en `lib/cocina.ts`). Las carpetas de mockups se eliminaron tras el merge.
- **PR #30 mergeado (squash `ddbca26`): división de cuenta por artículos en Caja móvil.** Calculadora en la pantalla de cobro: asignar artículos a personas → una línea de pago por persona con monto exacto (acumulación en centavos, sin prorrateo de IVA — los precios del detalle son finales). Solo móvil (`lib/split.ts` puro + UI en Cobro); un folio, N pagos.
- **PR #31 mergeado (squash `6feed1e`): varios pedidos por mesa (rondas).** Una mesa Ocupada acepta pedidos adicionales y se libera solo al cerrar el último activo (`tiene_pedido_activo(excepto_id_pedido)` en cobrar/cancelar); en el móvil las mesas Ocupadas son tocables (`mesaSeleccionable`). Sin cambios de esquema ni API.
- **PR #34 mergeado (squash `e3b2594`): configuración de EAS Build** — perfil `preview` en `mobile/eas.json` genera APK instalable con la API LAN horneada (`http://10.134.78.227:8000/api/v1`); `usesCleartextTraffic` vía `expo-build-properties` (el release de Android bloquea `http://` en claro); package `com.cafeteriaaroma.app`, nombre visible «Cafetería Aroma». El build corre en la nube de Expo con la cuenta del usuario (`npx eas build -p android --profile preview`).
- **PR #33 mergeado (squash `4b022bc`): logo oficial en el arranque del móvil** — splash nativo, pantalla de carga e ícono adaptativo desde `mobile/assets/images/logo-aroma.png` (fondo `#FEF8EA` muestreado del arte); el ícono del launcher solo se ve en build nativo, no en Expo Go.
- **PR #32 mergeado (squash `35b01e2`): cuenta por mesa — venta multi-pedido.** La FK se invirtió (`pedidos.id_venta` nullable reemplaza a `ventas.id_pedido`, migración `c3d5e7f9a1b2` con backfill — **ya aplicada a la BD real, 0 huérfanas**); `POST /ventas` acepta `ids_pedidos` (misma mesa; con varias rondas, todas Entregadas; repetidos 422) y `cobrar` bloquea los pedidos con `FOR UPDATE OF pedidos` contra el doble cobro concurrente. Caja móvil agrupa en cuentas por mesa (cuenta completa o ronda suelta) y la división del PR #30 opera sobre la unión de líneas con ticket/folio únicos. **Trabajo siguiente candidato:** camino de "cerrar sin cobro" para el pedido Entregado que nadie paga (deuda con prioridad operativa).
- **PR #35 mergeado (squash `2d54c8c`): clave demo `Cafeteria123`** (BD viva actualizada por PATCH; `seed.py` y docs alineados). **APK generado con EAS e instalado: operando OK.** Catálogo ampliado por API (solo datos, viven en el volumen de la BD): 24 productos activos todos con receta, 14 mesas, 27 insumos, categoría Desayunos y descripciones de categorías; duplicados del seed desactivados.
- Sin ramas residuales: las locales ya mergeadas se limpiaron el 2026-08-11.
- La colección **Postman fue eliminada** (agosto 2026); las pruebas manuales de API se hacen vía Swagger (`/docs`).

### Cobertura de tests
| Suite | Cantidad | Comando |
|---|---|---|
| Backend | 246 tests | `docker compose exec api pytest` |
| Web | 127 tests | `docker compose exec web pytest` |
| Móvil | 113 tests + `tsc` limpio | `cd mobile && npm test` |

> Las tres suites verificadas sobre `main` tras el merge del PR #32 (squash `35b01e2`).

Los tests de backend usan una **BD dedicada** (`<db>_test`, autoprovisionada con `seed_base`) con guardia que impide tocar la BD de dev.

---

## 3. Flujo de negocio (end-to-end, funcionando)

```
Mesero (móvil)          Cocina (móvil)           Mesero            Caja (móvil)
mesa → menú → carrito → Pendiente → En prep. → Listo → Entregado → cobro (IVA, pago,
→ confirmar pedido       (polling 10s, avanza estado)  (entrega)    cambio, ticket)
     │                                                                  │
     ├─ mesa Disponible→Ocupada                          libera la mesa ┘
     ├─ precio congelado en el pedido
     └─ descuento automático de stock por receta (kárdex; 422 si falta insumo;
        reposición al cancelar)
```

- **Estados del pedido:** flujo lineal Pendiente → En preparación → Listo → Entregado, con autorización por rol; cancelación con motivo libera la mesa.
- **Cobro:** venta 1:1 con el pedido, IVA desglosado (tasa en `configuracion.iva_tasa`), pagos con método, cambio, folio/ticket. El pago dividido está soportado por la API pero la UI móvil cobra con un solo método.
- **Inventario:** compra sube stock (kárdex Compra, costo por **promedio ponderado** a 2 decimales; si el inventario previo no tiene valor, toma el costo de la compra), pedido descuenta por receta (kárdex Salida/Venta), ajustes/mermas manuales con bloqueo de stock negativo y alerta de mínimo.
- **Gastos:** registro de egresos por categoría (guard Cajero/Admin).

---

## 4. Arquitectura por componente

### Backend (`backend/app/`)
- `api/v1/` — routers: `auth, usuarios, roles, mesas, categorias, productos, pedidos, estados, ventas, metodos_pago, gastos, unidades, insumos, recetas, proveedores, compras, reportes` (16 dominios).
- `services/` — lógica de negocio por dominio (patrón service layer).
- `models/` — SQLAlchemy: `usuario, mesa, producto, pedido, venta, gasto, inventario, compra, configuracion`.
- `schemas/` — Pydantic por dominio.
- `core/` — `config.py`, `security.py` (JWT + bcrypt), `deps.py` (`get_current_user`, `require_admin`).
- `db/` — `seed.py` (catálogos + admin + demo, idempotente), `seed_demo.py` (opt-in: ~60 días de ventas/gastos/compras deterministas para poblar reportes).
- `alembic/versions/` — dos revisiones: `a1557e1dd3bf` (esquema inicial, las 23 tablas del diccionario) y `7f3a9c2b1d84` (inventario a 3 decimales: amplía `insumos.stock_actual/stock_minimo`, `movimientos_inventario.cantidad` y `detalle_compra.cantidad` de `Numeric(10,2)` a `Numeric(10,3)`; recrea `detalle_compra.subtotal` porque es columna generada; el `downgrade` redondea el tercer decimal de forma irreversible).

**Auth:** JWT stateless — access 30 min + refresh 7 días. Roles: Administrador, Mesero, Cajero, Cocinero. El **admin principal está blindado**: no se le puede cambiar el rol por API (400, por `correo == ADMIN_CORREO`) y `seed_admin` es correctivo.

**Reportes (solo Admin):** `GET /reportes/{resumen, ventas-por-dia, top-productos, comparativo, inventario-niveles, ventas, gastos, estado-resultados?agrupar=dia|semana|mes}` con filtros de fechas y por entidad.

### Web (`web/app/`)
- Blueprints: `auth/` (login admin-only, `flask-login`, refresh-on-401), `usuarios/` (CRUD con avatares, badges, filtros, reactivar), `dashboard/` (Estadísticas: 6 KPIs con ▲/▼ %, dona con total al centro, Ventas vs Gastos con bucketing mensual, tendencia, inventario), `reportes/` (BI: 4 tipos — Ventas Detalladas, Gastos Operativos, Inventario, Estado de Resultados agrupado — con preview, gráfica y export).
- `services/api_client.py` + `api_gateway.py` — todo pasa por la API (el web no toca la BD); `services/export.py` — PDF (WeasyPrint, gráfica estática CSS) y XLSX (openpyxl, BarChart nativo).
- Tema **"Cafetería Aroma"** (rediseño PR #29): Lora (títulos/cifras) + Karla (UI) **vendorizadas** en `static/fonts/` (woff2 variables, sin CDN); paleta café/caramelo/crema en tokens de `app.css`; sidebar `#2B1E16` con logo de vapor e iconos SVG inline; login de dos paneles con imagen (`login.css` propio). Solo plantillas + CSS. `/` redirige a `/dashboard`.
- ⚠️ Tras registrar un blueprint nuevo hay que `docker compose restart web` (el hot-reload no recarga rutas).

### Móvil (`mobile/src/`)
- `app/` (expo-router): `login`, `seleccion-modulo`, `mesero/` (mesas, menú, carrito, mis-pedidos), `cocina/` (pedidos, recetas, receta-detalle, inventario, ajuste, compras, compra-detalle, compra-nueva), `caja/` (pendientes, cobro, gastos). Auto-navegación por rol al iniciar sesión.
- **Tema "Cafetería Aroma" (PR #29):** tokens en `src/theme/` y componentes base en `src/ui/` (`BottomNav` por rol con iconos SVG propios, `Badge`, `Chip`, `Stepper`, `Card`, `Input`, `PrimaryButton`); fuentes Lora/Karla vía `@expo-google-fonts` cargadas en `_layout.tsx`; `expo-print` para el botón Imprimir Ticket (`lib/ticket.ts` genera el HTML). Cerrar sesión pide confirmación (`confirmarSalir` en `ui/nav.ts`).
- `api/client.ts` — cliente axios con tipos; `api/coerce.ts` — **coacción Decimal string→number en el borde** (interceptor de respuesta, allowlist: `total, subtotal, iva, cambio, monto, cantidad, precio_venta, costo_unitario, stock_actual, stock_minimo`).
- `lib/` — lógica pura testeable por módulo + `format.ts` con el helper **`money()`** (`$X.XX` defensivo).
- `store/` — `auth.ts` (sesión en `expo-secure-store`; en web cae a `localStorage`), `cart.ts`.
- Polling (10s) para vistas en vivo; **refresh-on-401 global** vía interceptor de respuesta de axios con single-flight (rama `feat/fixes-logout-refresh-pagos`, lista para PR): N 401 concurrentes disparan un solo refresh, un reintento por petición, tokens renovados en el store + `SecureStore`; si el refresh falla, Alert único + `router.replace` al login. Complementa, no reemplaza, el patrón de **token como argumento** en las pantallas (`lib/authRefresh.ts` + `api/authInterceptor.ts`).

---

## 5. Convenciones y lecciones críticas (no romper)

1. **La API serializa `Decimal` como string en JSON.** En móvil: nunca `.toFixed()` directo — usar `money()` de `src/lib/format.ts`; la coacción de tipos vive en `coerce.ts` (si se agrega un campo monetario nuevo, añadirlo al allowlist `DECIMAL_FIELDS`). En web: coaccionar a `float` antes de sumar; los stubs de test usan **strings**, no floats.
2. **JS inline del dashboard web:** no declarar `const top`/`name`/`parent`/etc. — colisionan con globales `window.*` no-configurables y rompen todo el script (gráficas en blanco). Hay guard de lint.
3. **Canvas Chart.js** necesita contenedor con altura (`.chart-box` 260px) + `maintainAspectRatio:false`.
4. **No proponer Postman**: la colección fue eliminada; no generar evidencia del Runner.
5. Comparaciones de stock deben ser numéricas (el interceptor de coacción lo garantiza en móvil).
6. `main` siempre estable; ramas `feature/<modulo>-<descripcion>`; PR con revisión antes de merge.

---

## 6. Historial de sprints (PRs mergeados)

| Sprint | PRs | Entregable |
|---|---|---|
| 0 — Cimientos | — | Monorepo, docker-compose, migración 23 tablas, seeds, `GET /health` |
| 1 — Auth | #1–#3 | JWT + CRUD usuarios (API), panel Flask admin-only, login móvil + selección de módulo |
| 2 — Catálogo y pedidos | #4–#7 | CRUD mesas/categorías/productos, crear/consultar pedidos, flujo Mesero móvil |
| 3 — Cocina y estados | #8–#10 | Transiciones de estado + cancelar, pantalla Cocina, "Mis pedidos" en vivo |
| 4 — Caja *(hito crítico)* | #11–#13 | Cobro con IVA/pagos/cambio/ticket, Caja móvil, gastos |
| 5 — Inventario y compras | #14–#16 | Insumos + kárdex, recetas + descuento automático, compras a proveedores |
| 6 — Dashboard y BI | #17–#19 | Dashboard KPIs + gráficas, rediseño "Cafetería Aroma", analítica avanzada, Reportes BI con export PDF/XLSX, `seed_demo`, aislamiento de tests, hardening admin |
| Post-6 | #20 | Fix de raíz Decimal string→number en móvil (`coerce.ts` + `money()`) |
| Post-6 | #26 | Inventario y kárdex a 3 decimales: migración `7f3a9c2b1d84`, validación 422 en la API, `decimales.ts` + `cantidad()` en móvil, reporte de Inventario del panel sin truncar, fix de `seed_base` sobre BD vacía |
| Post-6 | #27 | Fixes menores: `/logout` por POST (logout-CSRF), refresh-on-401 global móvil (`authRefresh.ts` + `authInterceptor.ts`, single-flight y Alert único), test de API de pago dividido con excedente y referencia |
| Post-6 | #28 | Costo de insumo por promedio ponderado en las compras (`compra_service.py`) |
| Post-6 | #29 | Rediseño "Cafetería Aroma" web + móvil: fuentes Lora/Karla, theme/ui móvil con BottomNav por rol, ticket completo + Imprimir Ticket, detalle de compra, confirmación de logout, temporizador de Cocina |

---

## 7. Pendientes y deuda técnica

**Funcional:**
- CRUD de catálogo (mesas/categorías/productos) en el **panel web** — hoy solo vía API/Swagger. *(candidato a próximo sprint)*
- **Pago dividido** en la UI de Caja móvil (la API ya lo soporta; falta también test de pago dividido).
- **El panel web exige token CSRF** en sus 14 rutas POST (PR #25). Desplegar el panel requiere `docker compose up -d --build web`: las dependencias viven en la imagen, no en el volumen montado.
- **Estado de mesa `Ocupada` lo gestiona el sistema** (PR #24): la API responde 409 si se intenta cambiar el estado de una mesa con pedido activo (no cancelado y sin venta) y 422 si se asigna `"Ocupada"` a mano, tanto al crear como al editar. Consecuencia confirmada en uso: **un pedido Entregado que nadie paga deja la mesa trabada** — `cancelar` rechaza estados terminales y el guard impide liberarla, así que falta un camino de "cerrar sin cobro".
- **Recetas** con pantalla en Cocina móvil (PR #23). La cantidad se captura con **3 decimales** en toda la cadena: `cantidad_requerida` de la receta, `stock_actual`/`stock_minimo` del insumo, `MovimientoInventario.cantidad` del kárdex y `detalle_compra.cantidad` son todos `Numeric(10,3)` desde la migración `7f3a9c2b1d84`; la API rechaza con 422 cualquier cantidad de más de 3 decimales.
- RF-M03 (recuperar contraseña): solo nota, sin implementar.
- Widgets diferidos: rebanada "Otros" en la dona; capacidad real de almacén en nivel de inventario.

**Deuda menor (triada, no bloquea):**
- Los umbrales del temporizador de Cocina quedaron en **modo demo (1/2 min)**; para operación real subir `RETRASO_ALERTA_MIN`/`RETRASO_CRITICO_MIN` en `mobile/src/lib/cocina.ts` (p. ej. 10/15).
- La pantalla de detalle de compra busca la compra en `GET /compras` (la API no expone `GET /compras/{id}`); si la lista se pagina algún día, agregar el endpoint.
- Quitar código muerto `api_client.get_reporte_resumen`; relabel "# Pedidos" → "# Ventas"; paleta de dona (6 colores < límite 10); tests poco específicos; documentar `Pedido.id_usuario` (mesero) vs `Venta.id_usuario` (cajero); leyenda de dona acoplada a `Chart.overrides`; nombre de archivo de export no valida fechas (fechas inválidas → 500, no explotable).
- El kárdex no registra costo por movimiento: el promedio ponderado del insumo solo vive en su estado actual, sin histórico de valuación.
- Endpoints de detalle de reportes sin paginación (N+1 leve).
- Placeholder `modulo/[key].tsx` sin uso por ningún rol.
- Warning de deprecación `HTTP_422_UNPROCESSABLE_ENTITY` → `_CONTENT` (no rompe).

---

## 8. Cómo arrancar

```bash
cp .env.example .env                             # ajustar secretos (solo la primera vez)
docker compose up -d                             # db + api + web + adminer
docker compose exec api alembic upgrade head     # esquema al día (migraciones, a mano tras cada pull)
docker compose exec api python -m app.db.seed    # catálogos + admin + demo (idempotente)
docker compose exec api python -m app.db.seed_demo   # opcional: 60 días de datos demo para reportes
cd mobile && npx expo start                      # móvil
```

URLs: API `localhost:8000/docs` · Web `localhost:5000` · Adminer `localhost:8080`.

### Credenciales de prueba (creadas por el seed)
| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@cafeteria.com` | `Cafeteria123` |
| Mesero | `mesero@cafeteria.com` | `Cafeteria123` |
| Cajero | `cajero@cafeteria.com` | `Cafeteria123` |
| Cocinero | `cocinero@cafeteria.com` | `Cafeteria123` |

### Entorno (WSL2)
- Docker Desktop con integración WSL activada.
- Móvil en teléfono físico: `EXPO_PUBLIC_API_BASE_URL` con la **IP LAN de Windows** en `mobile/.env`, `npx expo start --tunnel`, y abrir el puerto 8000 en el Firewall de Windows.

---

## 9. Mapa de documentación

| Archivo | Contenido |
|---|---|
| `README.md` | Presentación y arranque rápido |
| `progress.md` | Bitácora detallada de avance por sprint (fuente canónica de estado) |
| `docs/superpowers/specs/` | 20 documentos de diseño por slice |
| `docs/superpowers/plans/` | 21 planes de implementación por slice |
| `CONTEXTO-PROYECTO.md` | Este documento (resumen integral de contexto) |
