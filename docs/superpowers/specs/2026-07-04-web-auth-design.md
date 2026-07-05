# Diseño — Panel Web Admin: login y gestión de usuarios (feature/web-auth)

**Fecha:** 2026-07-04
**Sprint:** 1 (slice: parte web + lógica de backend necesaria)
**Rama:** `feature/web-auth`

## Objetivo

Entregar el panel web administrativo (Flask) para que un **Administrador** inicie
sesión y gestione usuarios y roles, consumiendo la API FastAPI (nunca la BD
directamente). Incluye el enriquecimiento de la API necesario para mostrar el
nombre del rol.

Cubre: RF-L01..L05, RF-U01..U07, RF-G01..G05.

## Decisiones tomadas (brainstorming)

1. **Alcance:** login admin + gestión de usuarios/roles. Sin dashboard ni reportes.
2. **Nombre de rol:** se enriquece la API (`UsuarioOut` con `rol` anidado) — fuente
   única de verdad; el web solo muestra.
3. **Auth del web:** `flask-login` + tokens (access/refresh) en la sesión firmada de
   Flask, con refresh-on-401 en el cliente de API.
4. **Estilos:** CSS propio autocontenido, sin CDN externo.

## Parte A — Backend (enriquecimiento)

### Modelo `Usuario`
Añadir relación ORM (sin migración; solo mapeo):

```python
rol = relationship("Rol")
```

### Schema `UsuarioOut`
Anidar el rol (se conserva `id_rol` para formularios):

```python
class UsuarioOut(BaseModel):
    ...
    id_rol: int
    rol: RolOut
    ...
```

`RolOut` ya existe. Con `from_attributes`, Pydantic lee `usuario.rol`.

### Tests backend
Extender `test_auth_api.py` / `test_usuarios_api.py`: `/auth/me` y `POST /usuarios`
devuelven `rol.nombre_rol`. Verificar que la relación no rompe los 33 tests
existentes.

## Parte B — Panel Web (Flask)

**Regla de oro:** la web no se conecta a Postgres; toda la lógica de negocio vive
en la API. La web orquesta llamadas HTTP y renderiza.

### Estructura

```
web/app/
├── __init__.py              # app factory: config, login_manager, blueprints
├── config.py                # API_BASE_URL, SECRET_KEY desde entorno
├── services/
│   └── api_client.py        # cliente HTTP tipado hacia FastAPI
├── auth/
│   ├── __init__.py          # WebUser(UserMixin) + user_loader
│   └── routes.py            # blueprint auth: login, logout
├── usuarios/
│   └── routes.py            # blueprint usuarios: list, new, create, edit, update, toggle
├── templates/
│   ├── base.html            # layout, nav, flash messages
│   ├── auth/login.html
│   └── usuarios/{list,form}.html
└── static/css/app.css       # CSS propio, responsive, contraste AA
```

### `api_client.py`
Funciones que envuelven `requests` contra `API_BASE_URL`:

- `login(correo, password) -> dict` (tokens) — o lanza `ApiError` en 401.
- `get_me(access) -> dict`
- `list_usuarios(access, q=None) -> list[dict]`
- `get_usuario(access, id) -> dict`
- `create_usuario(access, payload) -> dict`
- `update_usuario(access, id, payload) -> dict`
- `delete_usuario(access, id) -> dict`
- `list_roles(access) -> list[dict]`

Excepción `ApiError(status_code, detail)` para traducir respuestas ≥400.
Un helper `refresh(refresh_token) -> dict` para el refresh-on-401.

### Auth (`flask-login`)
- `WebUser(UserMixin)`: `id`, `nombre`, `correo`, `rol` (nombre). `get_id()` = id.
- `user_loader`: reconstruye `WebUser` desde `session["user"]` (dict guardado al
  loguear); si no hay, devuelve `None`.
- Tokens en `session["access"]` / `session["refresh"]`.
- Helper `api_call(fn, *args)` que inyecta el access token; ante `ApiError(401)`
  intenta **un** `refresh`, actualiza la sesión y reintenta; si vuelve a fallar,
  `logout_user()` y redirige a login.

### Blueprint `auth`
- `GET /login`: formulario (RF-L01). Si ya autenticado, redirige a usuarios.
- `POST /login`: valida campos no vacíos (RF-L02); llama `api_client.login`; si 401
  → mensaje "credenciales incorrectas" (RF-L03); llama `get_me`; **si
  `rol != "Administrador"` → rechaza** (RF-L04, "acceso solo para administradores");
  si ok, guarda sesión + `login_user`, redirige a la lista de usuarios.
- Enlace de soporte visible en el login (RF-L05).
- `GET /logout`: `logout_user`, limpia sesión, redirige a login.

### Blueprint `usuarios` (todo `@login_required`)
- `GET /usuarios`: lista con nombre, rol, estado (RF-G01); búsqueda `?q=` (RF-G02);
  badges activo/inactivo (RF-G03); botones editar/desactivar (RF-G04); botón "nuevo"
  (RF-G05).
- `GET /usuarios/nuevo`: formulario de alta; carga roles vía `list_roles` (RF-U03);
  toggle mostrar/ocultar contraseña con JS mínimo (RF-U02); nota de permisos por rol
  (RF-U04); botón cancelar (RF-U06).
- `POST /usuarios`: arma payload y llama `create_usuario`. Éxito → redirige a lista
  con flash. `ApiError(409/422)` → re-renderiza el form con el mensaje (RF-U07
  correo duplicado). (RF-U05)
- `GET /usuarios/<id>/editar` + `POST /usuarios/<id>`: `update_usuario` (PATCH).
- `POST /usuarios/<id>/desactivar`: `delete_usuario` (soft-delete). Si el usuario
  intenta desactivarse a sí mismo, la API responde 409 y se muestra el mensaje.

### Estilos
`app.css` propio: layout con nav superior, tablas y formularios legibles,
responsive (escritorio y tableta, RNF), contraste AA. Sin recursos externos.

## Manejo de errores

| Situación | Comportamiento web |
|---|---|
| Login con credenciales malas | Re-render login con mensaje (RF-L03) |
| Login de usuario no-admin | Rechazo con mensaje "solo administradores" (RF-L04) |
| Access token expirado (401 en llamada) | Refresh automático; si falla, logout + login |
| Correo/usuario duplicado (409) al crear | Re-render form con mensaje |
| Validación (422) | Re-render form con mensaje |
| Ruta protegida sin sesión | Redirige a login (`login_required`) |
| Error de red hacia la API | Flash de error, sin crash |

## Testing

`pytest` con el test client de Flask y la capa `api_client` **mockeada**
(monkeypatch), sin API viva. Casos:

- `GET /login` responde 200 y muestra el formulario.
- Login admin OK → redirige a `/usuarios`, setea sesión.
- Login de no-admin → rechazado, sin sesión.
- Login credenciales malas → mensaje de error.
- `/usuarios` sin sesión → redirige a login.
- `/usuarios` con sesión → renderiza la tabla con nombre y rol.
- `POST /usuarios` válido → llama `create_usuario` y redirige.
- `POST /usuarios` con 409 → muestra el mensaje de duplicado.
- Logout limpia la sesión.

## Nota sobre RF-U01 (teléfono)

RF-U01 menciona capturar "teléfono", pero la entidad `usuarios` del diccionario de
datos (fijada en Sprint 0) **no tiene columna de teléfono**. El formulario de alta
captura: nombre, apellido paterno, apellido materno, correo, nombre de usuario,
contraseña y rol. El teléfono queda **omitido** para no introducir un campo fuera
del modelo de datos; se retomaría solo si el esquema se amplía (nueva migración),
lo cual está fuera de este slice.

## Fuera de alcance (YAGNI)

Dashboard y reportes (Sprint 6), recuperación de contraseña (más allá del enlace de
soporte), edición del propio perfil, gestión de catálogos, campo teléfono en
usuarios.
