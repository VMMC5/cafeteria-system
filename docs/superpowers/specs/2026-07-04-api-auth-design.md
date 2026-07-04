# Diseño — API de Autenticación y Usuarios (feature/api-auth)

**Fecha:** 2026-07-04
**Sprint:** 1 (slice: solo API)
**Rama:** `feature/api-auth`

## Objetivo

Proveer autenticación por JWT y gestión de usuarios/roles en la API FastAPI, de
modo que cada rol pueda autenticarse y que un Administrador pueda administrar el
personal del sistema. La web (Flask) y la app móvil (Expo) consumirán esta API en
ramas posteriores.

Cubre los requerimientos: RF-M01, RF-M02, RF-M04, RF-L01, RF-L04, RF-U01..U07,
RF-G01..G05.

## Decisiones tomadas (brainstorming)

1. **Alcance:** solo la API de autenticación + CRUD de usuarios/roles. Sin web ni móvil.
2. **Tokens:** access (30 min) + refresh (7 días), ambos JWT firmados HS256.
3. **Refresh stateless:** sin tabla en BD. En cada `/refresh` se recarga el usuario
   y se valida `activo`; desactivar a un usuario corta su capacidad de renovar.
4. **Admin inicial:** seed idempotente desde variables de `.env`.

## Endpoints (bajo `/api/v1`)

| Método | Ruta | Auth | Descripción | RF |
|---|---|---|---|---|
| POST | `/auth/login` | pública | `username`(=correo) + `password` (form OAuth2) → `{access_token, refresh_token, token_type}` | RF-M01, RF-L01 |
| POST | `/auth/refresh` | refresh token | Valida refresh, recarga usuario, verifica `activo`, **rota** y devuelve nuevo par | RF-M02 |
| GET | `/auth/me` | access | Usuario actual (id, nombre, correo, rol) | RF-M04, RF-L04 |
| GET | `/roles` | admin | Lista de roles (para el formulario de alta) | RF-U03 |
| GET | `/usuarios` | admin | Listar usuarios; búsqueda `?q=` por nombre/correo | RF-G01, RF-G02 |
| POST | `/usuarios` | admin | Crear usuario con rol asignado | RF-U01..U05 |
| GET | `/usuarios/{id}` | admin | Detalle de un usuario | — |
| PATCH | `/usuarios/{id}` | admin | Editar datos / activar / desactivar | RF-G03, RF-G04 |
| DELETE | `/usuarios/{id}` | admin | **Soft-delete** (`activo=false`, no borra la fila) | RF-G04 |

## Modelo de tokens (JWT HS256, `python-jose`)

- **Access token** (30 min): claims `sub`=`id_usuario`, `rol`=nombre del rol,
  `type="access"`, `exp`.
- **Refresh token** (7 días): claims `sub`, `type="refresh"`, `exp`.
- `/refresh`: decodifica el refresh, exige `type == "refresh"`, recarga el usuario
  de la BD y valida `activo`; si no, 401. Emite un **par nuevo** (rotación).
- Firma con `SECRET_KEY` del entorno.

### Cambios de configuración (`.env` / `.env.example`)

```
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_MINUTES=10080   # 7 días
ADMIN_CORREO=admin@cafeteria.local
ADMIN_PASSWORD=cambiar_en_local
ADMIN_NOMBRE=Administrador
```

`Settings` (pydantic-settings) suma estos campos.

## Componentes

### `core/security.py`
- **Hashing:** librería `bcrypt` **directamente** (no `passlib`) para evitar el
  warning conocido de `passlib 1.7.4` con `bcrypt 5.0` (ya instalado). Funciones
  `hash_password(str) -> str` y `verify_password(plain, hashed) -> bool`.
- **JWT:** `create_access_token(sub, rol)`, `create_refresh_token(sub)`,
  `decode_token(token) -> dict`. Manejo de expiración/firma inválida.

### `core/deps.py`
- `get_current_user`: `OAuth2PasswordBearer(tokenUrl="auth/login")` para el botón
  "Authorize" de Swagger. Decodifica access, exige `type=="access"`, carga usuario,
  valida `activo`. 401 si falla.
- `require_admin`: depende de `get_current_user` y exige rol Administrador; 403 si no.

### `schemas/`
- `auth.py`: `Token`, `TokenPayload`, `RefreshRequest`.
- `usuario.py`: `UsuarioCreate`, `UsuarioUpdate`, `UsuarioOut` (**sin**
  `contrasena_hash`). Validación de contraseña mínima (8 chars).
- `rol.py`: `RolOut`.

### `services/usuario_service.py`
Lógica de negocio (fuera de los routers): crear usuario (hashea contraseña, valida
unicidad de `correo`/`nombre_usuario` → 409, valida existencia de rol), actualizar,
soft-delete, listar con búsqueda, autenticar (verifica credenciales + `activo`).

### `api/v1/`
- `router.py`: `APIRouter` que agrega `auth`, `usuarios`, `roles` bajo `/api/v1`.
- `auth.py`, `usuarios.py`, `roles.py`: routers finos que delegan al service.
- `main.py` registra `router` de v1.

### Seed de admin (`db/seed.py`)
Función que crea el Administrador desde `.env` si no existe (busca por `correo`).
Idempotente. Se ejecuta junto al seed de catálogos.

## Manejo de errores

| Situación | Código |
|---|---|
| Credenciales inválidas en login | 401 |
| Token ausente/expirado/inválido | 401 |
| Usuario desactivado intenta usar/refrescar | 401 |
| Rol insuficiente (no admin) | 403 |
| `correo` o `nombre_usuario` duplicado | 409 |
| Rol inexistente al crear usuario | 422 |
| Usuario `{id}` inexistente | 404 |
| Un admin intenta desactivarse/soft-deletearse a sí mismo | 409 |

**Regla de negocio:** un Administrador no puede desactivar ni soft-deletear su
propia cuenta (evita el auto-bloqueo que dejaría al sistema sin acceso). El
`usuario_service` compara el `id` objetivo contra el del usuario autenticado.

## Testing (`pytest` dentro del contenedor)

`docker compose exec api pytest`. BD de test con rollback por test (fixture en
`conftest.py`). Casos:

- Login correcto devuelve access + refresh; credenciales malas → 401.
- `/auth/me` con access válido devuelve el usuario; sin token → 401.
- `/refresh` válido rota tokens; refresh expirado → 401; refresh de usuario
  desactivado → 401; access token usado como refresh → 401.
- CRUD de usuarios exige admin: sin token 401, con rol Mesero 403.
- Alta con `correo` duplicado → 409; contraseña corta → 422.
- Soft-delete deja `activo=false` y el usuario ya no puede loguear.
- `UsuarioOut` nunca expone `contrasena_hash`.

## Fuera de alcance (YAGNI)

Recuperación de contraseña (RF-M03/L05, prioridad baja/media), logout con
revocación real (elegimos stateless), rate-limiting, cambio de contraseña por el
propio usuario, web (Flask) y móvil (Expo) — todo en ramas/sprints posteriores.
