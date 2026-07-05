# Progreso — Sistema de Cafetería

**Repo:** [VMMC5/cafeteria-system](https://github.com/VMMC5/cafeteria-system) · **Rama principal:** `main`
**Última actualización:** 2026-07-05

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

### Cobertura de tests
- **Backend:** 68 tests (`docker compose exec api pytest`).
- **Móvil:** 23 tests jest (`cd mobile && npm test`) + `tsc` limpio.
- **Web:** 13 tests (`docker compose exec web pytest`).

---

## ⏳ Pendiente

### Sprint 3 — Cocina y ciclo de estados (SIGUIENTE)
- API: transiciones de estado del pedido (Pendiente → En preparación → Listo → Entregado) con validación de flujo.
- Móvil (Cocina): lista/filtro de pedidos, cambio de estado, notificación de "listo" al mesero (polling).
- Móvil (Mesero): estado en vivo del pedido, entrega, "Mis pedidos" (RF-M18..M26).

### Sprint 4 — Caja: cobro y ventas *(hito crítico)*
- API: cobrar pedido (venta 1:1), pagos con método y pago dividido, IVA y cambio, gastos.
- Móvil (Caja): pendientes de cobro, detalle con impuestos, flujo de pago, comprobante.

### Sprint 5 — Inventario y compras
- Recetas (`producto_insumo`), descuento automático de stock al confirmar pedido (kárdex), compras a proveedores.

### Sprint 6 — Dashboard y reportes
- Web: KPIs + gráficas (Chart.js), reportes con filtros y export PDF/XLSX.

### Deuda técnica / mejoras conocidas
- Módulos móviles **Caja** y **Cocina** siguen como placeholder (`modulo/[key].tsx`).
- CRUD de catálogo en la **web admin** (hoy solo vía API/Swagger).
- Warning de deprecación `HTTP_422_UNPROCESSABLE_ENTITY` → `_CONTENT` (no rompe).
- RF-M03 (recuperar contraseña) solo como nota; sin implementar.
- Sin refresh-on-401 global en el móvil (el bootstrap cubre la expiración al arrancar).

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

## Notas de entorno (WSL2)
- Docker requiere activar la integración WSL en Docker Desktop.
- Móvil en teléfono físico: `EXPO_PUBLIC_API_BASE_URL` con la **IP LAN de Windows** en `mobile/.env`, `npx expo start --tunnel`, y permitir el puerto 8000 en el Firewall.
- `web` en Expo: `expo-secure-store` no existe en web → se usa `localStorage` (ya resuelto).
