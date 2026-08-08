# Progreso — Sistema de Cafetería

**Repo:** [VMMC5/cafeteria-system](https://github.com/VMMC5/cafeteria-system) · **Rama principal:** `main`
**Última actualización:** 2026-08-08 (guard de mesa Ocupada en la API **mergeado a `main` — PR #24**, squash `bbe830d`; antes recetas en el módulo Cocina móvil, PR #23 `07aaeb7`)

Stack: **FastAPI** (API) · **Flask** (web admin) · **React Native + Expo** (móvil) · **PostgreSQL** · **Docker Compose**.
Metodología: cada slice pasa por brainstorming → spec → plan → implementación TDD → PR (specs y planes en `docs/superpowers/`).

---

## ✅ Completado

### Sprint 0 — Cimientos
- Monorepo (`backend/`, `web/`, `mobile/`, `docs/`) + `docker-compose` (db, api, web, adminer).
- Migración Alembic con **las 23 tablas** del diccionario + seed de catálogos.
- Smoke test: `GET /health` (API) y "Hola mundo" (web).

### Sprint 1 — Autenticación y usuarios
| PR | Qué |
|----|-----|
| **#1** API auth | Login JWT (access 30min + refresh 7d, stateless), bcrypt, `get_current_user`, `require_admin`, CRUD usuarios/roles, seed de admin |
| **#2** Web auth | Panel Flask: login admin-only + gestión de usuarios (consume la API, `flask-login`, refresh-on-401) |
| **#3** Móvil auth | Carga → login (sesión en `expo-secure-store`) → selección de módulo por rol |

### Sprint 2 — Catálogo y toma de pedidos
| PR | Qué |
|----|-----|
| **#4** API catálogo | CRUD mesas/categorías/productos (GET auth, escritura admin), borrado FK-safe, seed de 10 mesas + 7 productos |
| **#5** API pedidos | Crear pedido (precio congelado, mesa Disponible→Ocupada, total derivado), consultar pedidos |
| **#6** Móvil Mesero | Auto-navegación por rol + flujo mesas → menú → carrito → confirmar pedido |
| **#7** fix nav | Al iniciar sesión, el rol de un solo módulo aterriza directo en su panel (no en el botón intermedio) |

**Estado:** flujo **mesa → pedido** funciona de punta a punta (móvil Mesero + API + BD). Todos los PRs mergeados a `main`.

### Sprint 3 — Cocina y ciclo de estados
| PR | Qué |
|----|-----|
| **#8** API transiciones | `PATCH /pedidos/{id}/estado` (flujo lineal Pendiente→En preparación→Listo→Entregado, autorización por rol) + `POST /pedidos/{id}/cancelar` (motivo, libera mesa) |
| **#9** Móvil Cocina | `GET /estados` + `GET /pedidos?estados=1,2`; pantalla `/cocina` con lista de activos, polling 10s y avance de estado |
| **#10** Móvil Mesero en vivo | `getPedidos?mias=true&estados=`; pantalla "Mis pedidos" con estado en vivo (polling), Listo resaltado y entrega (Listo→Entregado) |

**Estado:** ciclo de vida del pedido completo **cocina ↔ mesero** en vivo. El pedido Entregado mantiene la mesa Ocupada (se libera en el cobro, Sprint 4).

### Sprint 4 — Caja: cobro y ventas *(hito crítico)*
| PR | Qué |
|----|-----|
| **#11** API cobro | `POST /ventas` (venta 1:1, pagos con método, IVA desglosado, cambio, ticket/folio, libera mesa) + `GET /ventas/{id}` + `GET /pedidos?por_cobrar=true`; IVA en `configuracion.iva_tasa` |
| **#12** Móvil Caja | `GET /metodos_pago`; `/caja` (pendientes, polling) → cobro (método + monto + cambio) → comprobante inline con desglose |
| **#13** Gastos | API `GET /gastos/categorias`, `POST/GET /gastos` (guard Cajero/Admin) + pantalla `/caja/gastos` (formulario + lista) |

**Estado:** flujo de negocio completo **pedido → cocina → mesero → cobro** de punta a punta. Cobro con IVA desglosado, pago (un método) y cambio; egresos registrables. Pago dividido en UI queda pendiente (la API ya lo soporta).

### Sprint 5 — Inventario y compras
| PR | Qué |
|----|-----|
| **#14** Insumos | `GET /unidades`, CRUD de insumos, `POST /insumos/{id}/movimientos` (ajuste/merma con kárdex, bloqueo de negativo); móvil Cocina `/cocina/inventario` (alerta de mínimo) + `/cocina/ajuste` |
| **#15** Recetas + descuento | CRUD `producto_insumo`; descuento automático de stock al confirmar pedido (kárdex Salida/Venta, **bloquea 422** si falta) y **reposición** al cancelar. Backend-only |
| **#16** Compras | `GET/POST /proveedores` (+ seed demo), `POST/GET /compras` (entrada de stock, kárdex Compra, actualiza costo al último); móvil `/cocina/compras` + `/cocina/compra-nueva` (multi-línea) |

**Estado:** inventario cerrado el ciclo: **compra sube stock**, **pedido descuenta** por receta, ajustes/mermas manuales, todo con kárdex. Recetas se gestionan por API.

### Sprint 6 — Dashboard, reportes y rediseño

**Mergeado a `main`:**
| PR | Qué |
|----|-----|
| **#17** Dashboard (Slice A) | API `GET /reportes/{resumen,ventas-por-dia,top-productos}` (solo Admin, filtro de fechas); web `/dashboard` con 6 KPIs, selector de periodo y 2 gráficas **Chart.js** (vendorizado local). `/` redirige a `/dashboard` |
| **#18** Rediseño web "Cafetería Aroma" | Tema café + **sidebar**, login split, Estadísticas (dashboard reskin), lista de usuarios (avatares, badges de rol, filtros Rol/Estado) y form de usuario (tarjetas de rol + permisos). Solo plantillas + CSS |
| **#19** Backlog (Slice B) | Todo lo listado abajo — analítica avanzada, Reportes BI, seed demo, aislamiento de tests y hardening del admin. Mergeado como `e1f2cb3` |

**Contenido del PR #19 (mergeado a `main`):**
- **Rediseño web "Cafetería Aroma"** (era PR #18, no llegó a `main`): tema café + sidebar, login split, reskin de Estadísticas/Usuarios/form de usuario. Plantillas + CSS.
- **`seed_usuarios_demo`** — recrea las 3 cuentas demo (mesero/cajero/cocinero, `cafeteria123`) idempotentemente.
- **Reportes filtrables + export (Slice B)**: base de `/reportes` con vista previa y descarga PDF (WeasyPrint) / XLSX (openpyxl tipado); ítem "Reportes" en sidebar; Dockerfile web con libs nativas (`pydyf==0.10.0`).
- **Analítica avanzada (Estadísticas)**: `GET /reportes/{comparativo,inventario-niveles}`; **KPIs ▲/▼ % con color por beneficio**, **dona con total al centro + leyenda %**, **Ventas vs Gastos** (barras agrupadas, presets Mes/6meses/Año con **bucketing mensual**), **tendencia con degradado**, **barras de inventario**, chips de indicadores (toggle cliente) y botón "Exportar vista". Layout de gráficas en rejilla 2×2.
- **`seed_demo`** (opt-in, `python -m app.db.seed_demo`): genera ~60 días de ventas/gastos/compras/insumos realistas (determinista, guard de idempotencia) para poblar reportes y estadísticas.
- **Aislamiento del suite de tests**: `conftest` usa una **BD de test dedicada** (`<db>_test`, autoprovisionada + `seed_base`), con **guardia** que falla si resolviera a la BD de dev. Desacopla los datos demo del panel de los tests.
- **Reactivar usuarios**: `POST /usuarios/<id>/activar` + botón "Activar" para inactivos en Usuarios y Roles.
- **Reportes BI** (herramienta de decisiones): dropdown de **4 tipos** (Ventas Detalladas, Gastos Operativos, Inventario, **Estado de Resultados agrupado**); **filtros por entidad** en la API (`/reportes/ventas` +usuario/método; `/reportes/gastos` +usuario/categoría; `/reportes/inventario-niveles` +solo_bajo_minimo; nuevo `/reportes/estado-resultados?agrupar=dia|semana|mes`); formulario dinámico (toggle de filtros por tipo, sin recargar); preview con fila de totales + **gráfica Chart.js** en el agrupado; **export PDF/XLSX de los 4 tipos** con **gráfica estática CSS en el PDF** (WeasyPrint no corre JS) y **BarChart nativo openpyxl** en el XLSX.
- **Hardening del admin principal**: `update_usuario` rechaza **400** el cambio de rol del admin principal (por `correo == ADMIN_CORREO`); `seed_admin` **correctivo** (restaura el rol si quedó mal).

**Estado:** Sprint 6 **completo, verificado y mergeado a `main`** (PR #19 `e1f2cb3`, 2026-07-08). Revisión final de rama completa: **READY TO MERGE** (0 Critical / 0 Important; los pendientes son deuda menor post-merge). Los conflictos con el PR #18 se resolvieron antes del merge (estrategia `--ours`, la rama era superset). Cada pieza pasó brainstorming → spec/plan → TDD subagent-driven → revisión de tarea + fixes; verificación visual/E2E en la app real (specs/planes en `docs/superpowers/`).

### Bugs de vista atrapados en verificación real (Estadísticas) — corregidos
- `TypeError`: la API serializa `Decimal` como **string**; coacción a `float` antes de sumar (los stubs de test ahora usan strings).
- Gráficas en blanco: `const top` colisiona con `window.top` (global no-configurable) → renombrado `topData`; guard de lint contra globales reservados.
- Canvas Chart.js sin altura → `.chart-box` (260px) + `maintainAspectRatio:false`.

### Post-Sprint 6 — fix de importes en móvil (PR #20 `0993569`)
Al probar la app en dispositivo físico varias pantallas reventaban con `Render Error: undefined is not a function` al pintar importes: la API serializa `Decimal` como **string** pero los tipos de `client.ts` los declaraban `number`, y `item.total.toFixed(2)` sobre un string rompe (mismo bug que en la web, ver `web/`).
- **Fix de raíz** (`mobile/src/api/coerce.ts` + interceptor de respuesta de axios): coacciona string→number en el **borde** del api-client (`total, subtotal, iva, cambio, monto, cantidad, precio_venta, costo_unitario, stock_actual, stock_minimo`; lista validada contra la API real). Los tipos `number` quedan verdaderos en runtime.
- **Helper `money()`** (`mobile/src/lib/format.ts`) para formateo defensivo `$X.XX` en Caja, Cobro/comprobante, Compras, Gastos y precio del menú.
- Efecto colateral: `stockBajo` comparaba strings (lexicográfico, bug latente) → ahora numérico correcto.
- Revisión de código: corregida la regresión de formato del precio del menú; el stock se deja como "12" (más limpio que "12.00") a propósito.

### Post-Sprint 6 — Catálogo en la web admin
CRUD completo de Productos/Categorías/Mesas desde el panel Flask (antes solo vía API/Swagger).
- **`api_client`**: 14 funciones nuevas (`list_/get_/create_/update_` para productos, categorías y mesas, más `delete_categoria`/`delete_mesa`).
- **Blueprint `catalogo`** (`web/app/catalogo/routes.py`, prefijo `/catalogo`) con 3 sub-recursos y navegación por pestañas (`_tabs.html`, activa según `request.endpoint`); `/catalogo` redirige a `/catalogo/productos`. Entrada "Catálogo" en el sidebar, entre Usuarios y Reportes.
- **Semántica de borrado por recurso**: Productos usa **toggle** Activar/Desactivar (`disponible`, no hay DELETE real); Categorías y Mesas usan **DELETE FK-safe** — si el recurso tiene productos/pedidos asociados, la API devuelve el error como flash y la lista sobrevive.
- **Regla de mesa Ocupada**: el form de una mesa en estado Ocupada no ofrece selector de estado (`_payload_mesa` solo manda `estado` si el campo vino en el POST), así el panel nunca pisa una mesa que el flujo de pedidos está gestionando.
- Precios como Decimal-string (mismo patrón que Estadísticas): templates y stubs de test usan strings, no floats.
- **26 tests nuevos** (5 de Task 1 sobre `api_client` + 21 en `test_catalogo.py`): 86 → **112** tests web.
- Verificación end-to-end contra la API real (worktree Flask en :5001, DB con seed): login admin, `/catalogo` → 302 a productos, las 3 pestañas cargan 200 con nombres de producto/categoría y mesas seed, precios `$ 30.00`…`$ 85.00`, Mesa 1 (Ocupada) con badge, sidebar con "Catálogo" activo.

### Post-Sprint 6 — Pago dividido en la Caja móvil
La pantalla de cobro mandaba un solo método de pago aunque la API ya soportaba varios (`POST /ventas` acepta `pagos: [...]`). Ahora Cobro soporta una **lista dinámica de líneas de pago**.
- **Lógica pura** (`mobile/src/lib/caja.ts`): agregar/quitar líneas de pago; `puedeCobrarPagos` valida que la suma cubra el total y aplica la **regla de excedente solo-Efectivo** (el cambio solo se permite si el sobrante queda cubierto por una línea en Efectivo, nunca en Tarjeta/Transferencia/Otro); `aPayload` arma el array de pagos para la API con `referencia` opcional (trim, se omite si queda vacía) solo en métodos no-Efectivo.
- **Pantalla de Cobro**: líneas de pago dinámicas (método + monto + referencia condicional para no-Efectivo), resumen de suma/faltante/cambio, aviso de excedente en método no-Efectivo, comprobante final lista cada pago con su referencia.
- Tipo del cliente API (`cobrarVenta`) ampliado con `referencia?` opcional por línea de pago.
- **67 tests móviles** (58 → 67, 11 nuevos) + `tsc --noEmit` limpio.
- **Smoke contra la API real** (`docker compose up -d db api`, login cajero, pedido de prueba mesa Disponible + producto del seed, `POST /api/v1/ventas` con `pagos: [Efectivo con excedente, Tarjeta con referencia: "V-123"]`): **201**, `pagos[1].referencia == "V-123"`, `cambio == suma − total` (Decimal-strings) — payload de `aPayload` validado end-to-end.

### Cobertura de tests
- **Backend:** 201 tests (`docker compose exec api pytest`).
- **Web:** 112 tests (`docker compose exec web pytest`) — incluye el módulo Catálogo (26 tests nuevos).
- **Móvil:** 67 tests jest (`cd mobile && npm test`) + `tsc` limpio.

---

## ⏳ Pendiente

### Próximo
- **Guard de mesa Ocupada en la API mergeado a `main` (PR #24, squash `bbe830d`)** — cierra ese diferido del review del PR #21. Backend **217/217** verificado post-merge. La suite web (114/114) no es evidencia del guard: stubea el cliente API con monkeypatch y nunca llama a la API real; el panel se verificó por inspección de código (`mesa_crear`/`mesa_actualizar` capturan `ApiError` y muestran `detail` como flash) más recorrido manual en móvil y web.
- **Siguiente slice: hardening CSRF del panel web** (el otro diferido del PR #21). No hay `flask-wtf` en `requirements.txt`; son 14 rutas POST (login, 4 de usuarios, 9 de catálogo) y 9 plantillas con formulario, y activar `CSRFProtect` rompe las 26 llamadas `client.post` de los tests si no se ajusta la config de test.
- **Candidato con prioridad tras el hallazgo confirmado:** camino de "cerrar sin cobro" para el pedido entregado que nadie paga (ver Deuda técnica).
- Recetas en Cocina móvil **mergeado a `main` (PR #23, squash `07aaeb7`)**. Suites post-merge: móvil 79/79 + `tsc --noEmit` limpio; backend **206/206** (la falla de `test_seed_admin` que arrastraba la suite se corrigió aparte, `6e154c3`). Smoke manual en dispositivo **ejecutado y OK** (alta, edición inline, selector sin duplicados, baja con confirmación, rechazo de 3 decimales). Candidato siguiente: migración del inventario a 3 decimales (ver deuda técnica).
- Pago dividido en Caja móvil **mergeado a `main` (PR #22, squash `7021077`)**; suite móvil 70/70 verificada post-merge. Pendientes del PR #22: smoke manual del cobro dividido en la app y test de API para venta con pagos múltiples.
- Widgets analíticos diferidos: rebanada "Otros" en la dona; capacidad real de almacén para el nivel de inventario.

### Deuda técnica / mejoras conocidas
- Guard de mesa Ocupada: la API rechaza cambiar el estado de una mesa con pedido activo (409) y asignar "Ocupada" a mano (422). La web mantiene su propio aviso mirando la bandera `mesa.estado`, así que en el caso raro de una mesa marcada Ocupada sin pedido activo el panel seguirá bloqueando el cambio aunque la API lo permita; destrabarla se hace por API.
- **Pedido entregado sin cobrar traba la mesa sin salida limpia — CONFIRMADO en móvil y web (2026-08-08).** `pedido_service.cancelar` rechaza pedidos en estado terminal (Entregado, Cancelado) con 409, y el guard rechaza liberar la mesa mientras ese pedido siga activo; la única salida hoy es registrar una venta que nunca ocurrió. Falta un camino de "cerrar sin cobro" (p. ej. permitir cancelar un Entregado con motivo, o un endpoint de cierre sin venta que libere la mesa dejando rastro). Es el candidato con más prioridad operativa.
- `venta_service.cobrar` y `pedido_service.cancelar` ponen `mesa.estado = "Disponible"` sin condición, sin consultar si la mesa tiene otro pedido activo. Hoy no es alcanzable (`crear` exige mesa Disponible, así que una mesa no puede acumular dos pedidos), pero ya que existe `tiene_pedido_activo` ambos sitios deberían consultarlo.
- **Deuda menor post-merge (triada en la revisión final, no bloquea):** quitar código muerto `api_client.get_reporte_resumen`; relabel "# Pedidos" → "# Ventas"; paleta de dona (6 colores < `limite` 10); un par de tests poco específicos; tests de no-regresión de filtros usan subconjunto en vez de igualdad; documentar `Pedido.id_usuario` (mesero) vs `Venta.id_usuario` (cajero) a nivel de modelo; la leyenda de la dona acopla a `Chart.overrides` (revisar en upgrade de Chart.js); el nombre de archivo del export refleja `desde`/`hasta` sin validar (fechas inválidas → 500, no explotable).
- Módulos móviles Mesero/Cocina/Caja implementados; el placeholder `modulo/[key].tsx` ya no se usa por ningún rol.
- Recetas: gestión completa desde el móvil (Cocina → Recetas). La lista de productos no muestra el nº de líneas de receta (`GET /productos` no lo trae); se ve al entrar al detalle.
- **Costo de insumo** por compra = último costo (no promedio ponderado).
- Warning de deprecación `HTTP_422_UNPROCESSABLE_ENTITY` → `_CONTENT` (no rompe).
- RF-M03 (recuperar contraseña) solo como nota; sin implementar.
- Sin refresh-on-401 global en el móvil (el bootstrap cubre la expiración al arrancar).
- Los endpoints de detalle de reportes no paginan (N+1 leve en ventas); falta test de API para venta con pagos múltiples.
- Tras registrar un blueprint nuevo en el web, hay que **reiniciar el contenedor** (`docker compose restart web`); el hot-reload no recarga el registro de rutas.
- `seed_admin` **no resincroniza la contraseña** de un admin existente (solo restaura el rol): cambiar `ADMIN_PASSWORD` en `.env` no surte efecto sobre una BD ya sembrada; hay que cambiarla por el PATCH de la API. Se evaluó hacer `.env` autoritativo y se descartó: un seed rutinario revertiría silenciosamente una contraseña cambiada desde el panel. El test de `seed_admin` ya no depende de esa coincidencia (`6e154c3`).
- Inventario a 2 decimales vs. `cantidad_requerida` a 3: `cantidadValida` (móvil) limita la cantidad de receta a 2 decimales para no desincronizar stock/kárdex; pendiente migración Alembic para ampliar el inventario a 3 decimales (revisar también reportes web).

---

## Cómo arrancar
```bash
docker compose up -d              # db + api + web + adminer
docker compose exec api python -m app.db.seed   # catálogos + admin + demo (idempotente)
cd mobile && npx expo start       # móvil (poner IP LAN en mobile/.env para teléfono físico)
```
URLs: API `localhost:8000/docs` · Web `localhost:5000` · Adminer `localhost:8080`.

## Credenciales de prueba
| Rol | Correo | Contraseña |
|-----|--------|-----------|
| Administrador | `admin@cafeteria.com` | `cafeteria123` |
| Mesero | `mesero@cafeteria.com` | `cafeteria123` |
| Cajero | `cajero@cafeteria.com` | `cafeteria123` |
| Cocinero | `cocinero@cafeteria.com` | `cafeteria123` |

> Las 4 cuentas las crea el seed (`seed_admin` + `seed_usuarios_demo`, idempotentes). El admin principal está **blindado**: su rol no se puede cambiar por API (400) y `seed_admin` lo restaura si quedara mal. El panel web es **admin-only** (rol Administrador).

## Notas de entorno (WSL2)
- Docker requiere activar la integración WSL en Docker Desktop.
- Móvil en teléfono físico: `EXPO_PUBLIC_API_BASE_URL` con la **IP LAN de Windows** en `mobile/.env`, `npx expo start --tunnel`, y permitir el puerto 8000 en el Firewall.
- `web` en Expo: `expo-secure-store` no existe en web → se usa `localStorage` (ya resuelto).
