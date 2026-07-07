# Progreso — Sistema de Cafetería

**Repo:** [VMMC5/cafeteria-system](https://github.com/VMMC5/cafeteria-system) · **Rama principal:** `main`
**Última actualización:** 2026-07-07 (Sprint 6: Slice A + rediseño mergeados; backlog en local sin subir)

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

**En local (rama `feature/sprint6-backlog`, commits locales — aún NO subido a GitHub):**
- **`seed_usuarios_demo`** — el seed recrea las 3 cuentas demo (mesero/cajero/cocinero, `cafeteria123`) idempotentemente.
- **Slice B — Reportes filtrables + export**: API `GET /reportes/{ventas,gastos}` (detalle); web `/reportes` (tipo Ventas/Gastos, rango, vista previa, **descargar PDF (WeasyPrint) / XLSX (openpyxl con celdas tipadas)**); ítem "Reportes" en sidebar; Dockerfile del web con libs nativas (`pydyf==0.10.0` fijado).
- **Analítica avanzada** (Estadísticas): API `GET /reportes/comparativo` (vs periodo anterior) y `/reportes/inventario-niveles`; web con **KPIs ▲/▼ % y color por beneficio** (Gastos ▲ = rojo, lógica en la ruta Flask y testeada), **dona** de productos, **tendencia** de pedidos y **barras de nivel de inventario**.
- **Hardening del admin principal**: `update_usuario` rechaza **400** si se intenta cambiar el `id_rol` del admin principal (identificado por `correo == ADMIN_CORREO`, no por id) a un rol distinto de Administrador; `seed_admin` ahora es **correctivo** (restaura el rol si quedó mal). Motivado por un incidente de datos de dev donde el admin quedó con rol Cajero y no podía entrar al panel (corregido con `UPDATE` en la BD local).

**Estado:** Sprint 6 funcionalmente completo. Slice A y rediseño en `main`; el resto (reportes+export, analítica, hardening) validado en local, pendiente de subir. Cada pieza pasó brainstorming → spec → plan → TDD con subagentes + revisión (specs/planes en `docs/superpowers/`).

### Cobertura de tests
- **Backend:** 174 tests (`docker compose exec api pytest`).
- **Móvil:** 53 tests jest (`cd mobile && npm test`) + `tsc` limpio.
- **Web:** 40 tests (`docker compose exec web pytest`).

---

## ⏳ Pendiente

### Próximo (continuar en local)
- **Subir el backlog local** (`feature/sprint6-backlog`, ~12 commits de código) a GitHub como PR(s) cuando se decida.
- Widgets analíticos diferidos: rebanada "Otros" en la dona; capacidad real de almacén para el nivel de inventario.
- Tipos de reporte extra (Productos/Inventario/Pedidos) y filtros (categoría/usuario/método/agrupar-por) en `/reportes`.

### Deuda técnica / mejoras conocidas
- Módulos móviles Mesero/Cocina/Caja implementados; el placeholder `modulo/[key].tsx` ya no se usa por ningún rol.
- **Pago dividido** en la Caja móvil: la API lo soporta, pero la UI cobra con un solo método.
- **Recetas** se gestionan solo por API (Swagger); sin pantalla móvil.
- **Costo de insumo** por compra = último costo (no promedio ponderado).
- CRUD de catálogo en la **web admin** (hoy solo vía API/Swagger).
- Warning de deprecación `HTTP_422_UNPROCESSABLE_ENTITY` → `_CONTENT` (no rompe).
- RF-M03 (recuperar contraseña) solo como nota; sin implementar.
- Sin refresh-on-401 global en el móvil (el bootstrap cubre la expiración al arrancar).
- **Reportes (Slice B):** los endpoints de detalle no paginan (N+1 leve en ventas); endurecer el nombre de archivo del export; falta test de pago dividido.
- **Analítica:** quitar `api_client.get_reporte_resumen` (código muerto tras el comparativo); afinar un par de tests poco específicos; relabel "# Pedidos" → "# Ventas".
- Tras agregar/registrar un blueprint nuevo en el web, hay que **reiniciar el contenedor** (`docker compose restart web`); el hot-reload no recarga el registro de rutas.

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
| Administrador | `admin@cafeteria.com` | `cambiar_en_local` |
| Mesero | `mesero@cafeteria.com` | `cafeteria123` |
| Cajero | `cajero@cafeteria.com` | `cafeteria123` |
| Cocinero | `cocinero@cafeteria.com` | `cafeteria123` |

> Las 4 cuentas las crea el seed (`seed_admin` + `seed_usuarios_demo`, idempotentes). El admin principal está **blindado**: su rol no se puede cambiar por API (400) y `seed_admin` lo restaura si quedara mal. El panel web es **admin-only** (rol Administrador).

## Notas de entorno (WSL2)
- Docker requiere activar la integración WSL en Docker Desktop.
- Móvil en teléfono físico: `EXPO_PUBLIC_API_BASE_URL` con la **IP LAN de Windows** en `mobile/.env`, `npx expo start --tunnel`, y permitir el puerto 8000 en el Firewall.
- `web` en Expo: `expo-secure-store` no existe en web → se usa `localStorage` (ya resuelto).
