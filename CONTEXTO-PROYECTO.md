# Contexto del Proyecto — Cafeteria-System

> Documento de contexto integral para retomar el proyecto en cualquier sesión (humana o con IA).
> **Generado:** 2026-08-04 · **Actualizado:** 2026-08-06 · **Repo:** [VMMC5/cafeteria-system](https://github.com/VMMC5/cafeteria-system) · **Rama principal:** `main`

---

## 1. ¿Qué es?

Sistema integral de gestión para una cafetería ("Cafetería Aroma"): automatiza **pedidos, cocina, cobro, inventario, compras, gastos y reportes**. Consta de tres aplicaciones que comparten una sola API:

| Componente | Tecnología | Rol |
|---|---|---|
| `backend/` | **Python + FastAPI** + SQLAlchemy + Alembic | API REST (fuente única de verdad, JWT) |
| `web/` | **Flask** + Jinja2 + Chart.js (vendorizado) | Panel de administración (admin-only): usuarios, dashboard, estadísticas, reportes BI con export PDF/XLSX |
| `mobile/` | **React Native + Expo** (expo-router, TypeScript) | App operativa por rol: Mesero, Cocina, Caja |
| BD | **PostgreSQL 16** | 23 tablas (migración Alembic única + seeds) |
| Infra | **Docker Compose** | Servicios: `db`, `api` (:8000), `web` (:5000), `adminer` (:8080). El móvil corre fuera de Docker con Expo. |

**Metodología:** cada slice pasa por brainstorming → spec → plan → implementación TDD → PR. Los specs y planes viven en `docs/superpowers/specs/` y `docs/superpowers/plans/` (21 planes, 20 specs).

---

## 2. Estado actual (agosto 2026)

- **Sprints 0–6 completos y mergeados a `main`** (PRs #1–#19) + **PR #20** (fix de importes en móvil) + **PR #21** (módulo Catálogo en el panel web) + **PR #22** (pago dividido en Caja móvil). No hay trabajo activo en curso.
- Ramas locales residuales ya mergeadas: `feature/compras`, `feature/dashboard`, `feature/web-redesign`.
- La colección **Postman fue eliminada** (agosto 2026); las pruebas manuales de API se hacen vía Swagger (`/docs`).

### Cobertura de tests
| Suite | Cantidad | Comando |
|---|---|---|
| Backend | 201 tests | `docker compose exec api pytest` |
| Web | 114 tests | `docker compose exec web pytest` |
| Móvil | 70 tests + `tsc` limpio | `cd mobile && npm test` |

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
- **Inventario:** compra sube stock (kárdex Compra, costo = último costo), pedido descuenta por receta (kárdex Salida/Venta), ajustes/mermas manuales con bloqueo de stock negativo y alerta de mínimo.
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
- `alembic/versions/a1557e1dd3bf_…` — migración única con las 23 tablas del diccionario.

**Auth:** JWT stateless — access 30 min + refresh 7 días. Roles: Administrador, Mesero, Cajero, Cocinero. El **admin principal está blindado**: no se le puede cambiar el rol por API (400, por `correo == ADMIN_CORREO`) y `seed_admin` es correctivo.

**Reportes (solo Admin):** `GET /reportes/{resumen, ventas-por-dia, top-productos, comparativo, inventario-niveles, ventas, gastos, estado-resultados?agrupar=dia|semana|mes}` con filtros de fechas y por entidad.

### Web (`web/app/`)
- Blueprints: `auth/` (login admin-only, `flask-login`, refresh-on-401), `usuarios/` (CRUD con avatares, badges, filtros, reactivar), `dashboard/` (Estadísticas: 6 KPIs con ▲/▼ %, dona con total al centro, Ventas vs Gastos con bucketing mensual, tendencia, inventario), `reportes/` (BI: 4 tipos — Ventas Detalladas, Gastos Operativos, Inventario, Estado de Resultados agrupado — con preview, gráfica y export).
- `services/api_client.py` + `api_gateway.py` — todo pasa por la API (el web no toca la BD); `services/export.py` — PDF (WeasyPrint, gráfica estática CSS) y XLSX (openpyxl, BarChart nativo).
- Tema **"Cafetería Aroma"**: paleta café + sidebar; solo plantillas + CSS. `/` redirige a `/dashboard`.
- ⚠️ Tras registrar un blueprint nuevo hay que `docker compose restart web` (el hot-reload no recarga rutas).

### Móvil (`mobile/src/`)
- `app/` (expo-router): `login`, `seleccion-modulo`, `mesero/` (mesas, menú, carrito, mis-pedidos), `cocina/` (pedidos, inventario, ajuste, compras, compra-nueva), `caja/` (pendientes, cobro, gastos). Auto-navegación por rol al iniciar sesión.
- `api/client.ts` — cliente axios con tipos; `api/coerce.ts` — **coacción Decimal string→number en el borde** (interceptor de respuesta, allowlist: `total, subtotal, iva, cambio, monto, cantidad, precio_venta, costo_unitario, stock_actual, stock_minimo`).
- `lib/` — lógica pura testeable por módulo + `format.ts` con el helper **`money()`** (`$X.XX` defensivo).
- `store/` — `auth.ts` (sesión en `expo-secure-store`; en web cae a `localStorage`), `cart.ts`.
- Polling (10s) para vistas en vivo; sin refresh-on-401 global (el bootstrap cubre expiración al arrancar).

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

---

## 7. Pendientes y deuda técnica

**Funcional:**
- CRUD de catálogo (mesas/categorías/productos) en el **panel web** — hoy solo vía API/Swagger. *(candidato a próximo sprint)*
- **Pago dividido** en la UI de Caja móvil (la API ya lo soporta; falta también test de pago dividido).
- **Recetas** sin pantalla (solo API/Swagger).
- RF-M03 (recuperar contraseña): solo nota, sin implementar.
- Widgets diferidos: rebanada "Otros" en la dona; capacidad real de almacén en nivel de inventario.

**Deuda menor (triada, no bloquea):**
- Quitar código muerto `api_client.get_reporte_resumen`; relabel "# Pedidos" → "# Ventas"; paleta de dona (6 colores < límite 10); tests poco específicos; documentar `Pedido.id_usuario` (mesero) vs `Venta.id_usuario` (cajero); leyenda de dona acoplada a `Chart.overrides`; nombre de archivo de export no valida fechas (fechas inválidas → 500, no explotable).
- Costo de insumo = último costo (no promedio ponderado).
- Endpoints de detalle de reportes sin paginación (N+1 leve).
- Placeholder `modulo/[key].tsx` sin uso por ningún rol.
- Warning de deprecación `HTTP_422_UNPROCESSABLE_ENTITY` → `_CONTENT` (no rompe).

---

## 8. Cómo arrancar

```bash
cp .env.example .env                             # ajustar secretos (solo la primera vez)
docker compose up -d                             # db + api + web + adminer
docker compose exec api python -m app.db.seed    # catálogos + admin + demo (idempotente)
docker compose exec api python -m app.db.seed_demo   # opcional: 60 días de datos demo para reportes
cd mobile && npx expo start                      # móvil
```

URLs: API `localhost:8000/docs` · Web `localhost:5000` · Adminer `localhost:8080`.

### Credenciales de prueba (creadas por el seed)
| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@cafeteria.com` | `cafeteria123` |
| Mesero | `mesero@cafeteria.com` | `cafeteria123` |
| Cajero | `cajero@cafeteria.com` | `cafeteria123` |
| Cocinero | `cocinero@cafeteria.com` | `cafeteria123` |

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
