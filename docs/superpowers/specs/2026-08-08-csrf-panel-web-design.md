# Spec — CSRF en el panel web

**Fecha:** 2026-08-08 · **Estado:** aprobado en brainstorming

## Objetivo

Cerrar el segundo pendiente diferido del review del PR #21: el panel Flask no tiene ninguna protección CSRF. `flask-wtf` ni siquiera está instalado, así que hoy cualquier página externa puede hacer que el navegador de un administrador autenticado dispare un POST al panel — crear o desactivar usuarios, borrar mesas y categorías, o alternar la disponibilidad de productos — porque la sesión viaja en cookie y se envía sola.

## Alcance

Solo `web/`. La API no necesita CSRF: es stateless y autentica con JWT en el header `Authorization`, que un formulario cross-site no puede fijar. El guard de mesa Ocupada (el otro diferido del mismo review) ya se cerró en el PR #24.

## Decisiones tomadas (brainstorming)

- **`Flask-WTF` con `CSRFProtect(app)` global**, no una implementación propia: reimplementar generación de token, comparación en tiempo constante y expiración es superficie de bug gratuita. `CSRFProtect` cubre las 14 rutas POST sin decorar ninguna.
- **Manejador de error propio** para el rechazo, porque el token vence a la hora y un formulario abierto en otra pestaña lo va a producir en uso normal.
- **Fuera:** cookie `SameSite` (decisión explícita del owner), `SESSION_COOKIE_SECURE` (rompería el login en HTTP local) y cualquier cambio en la API.

## Superficie protegida

14 rutas POST: `auth` (login), `usuarios` (crear, editar, desactivar, activar) y `catalogo` (9: productos crear/editar/toggle, categorías crear/editar/eliminar, mesas crear/editar/eliminar).

El panel **no usa `fetch` ni `XMLHttpRequest`** en ninguna plantilla ni en su JS propio: todos los POST son formularios HTML clásicos. Por eso no hace falta inyectar el token en cabeceras ni tocar JavaScript.

## Cambios

### `web/requirements.txt`
Añadir `Flask-WTF==1.3.0` y su dependencia transitiva `WTForms==3.2.2` (versiones verificadas como disponibles desde el contenedor). El archivo pinea todo, incluidas las transitivas de Flask (`blinker`, `itsdangerous`, `MarkupSafe`), así que ambas van explícitas. **Requiere reconstruir la imagen** (`docker compose build web`); reiniciar el contenedor no basta.

### `web/app/__init__.py`
Instanciar `CSRFProtect` a nivel de módulo (junto a `login_manager`) e inicializarlo con `csrf.init_app(app)` dentro de `create_app`, antes de registrar los blueprints.

### Las 10 plantillas con formulario
Añadir `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` como primer elemento dentro de cada `<form method="post">`:

| Plantilla | Formularios |
|---|---|
| `auth/login.html` | 1 |
| `usuarios/form.html` | 1 |
| `usuarios/list.html` | 2 (desactivar, activar — dentro del bucle de usuarios) |
| `catalogo/productos_form.html` | 1 |
| `catalogo/productos_list.html` | 1 (toggle — dentro del bucle) |
| `catalogo/categorias_form.html` | 1 |
| `catalogo/categorias_list.html` | 1 (eliminar — dentro del bucle) |
| `catalogo/mesas_form.html` | 1 |
| `catalogo/mesas_list.html` | 1 (eliminar — dentro del bucle) |

Los cuatro que viven dentro de bucles llevan el token **dentro** del `for`, para que cada fila emita el suyo.

### Manejador de `CSRFError`
En `create_app`, un `@app.errorhandler(CSRFError)` que renderice una plantilla nueva (`errors/csrf.html`) con el aviso de que la sesión o el formulario expiró y un enlace para volver, devolviendo **400**.

Se devuelve 400 y no un redirect por dos razones: es el código correcto para una petición rechazada, y es el patrón que el panel ya usa — `catalogo/routes.py` responde `render_template(...), e.status_code` ante un `ApiError`. Un 302 escondería el rechazo detrás de un código de éxito.

La plantilla extiende el `base.html` existente para conservar la navegación.

## Tests

### El problema
Hay **26 llamadas `client.post`** repartidas en 6 archivos (`test_auth.py`, `test_usuarios.py`, `test_catalogo.py`, `test_dashboard.py`, `test_reportes.py`, `test_web_ui.py`). Con `CSRFProtect` activo todas fallarían con 400.

### La solución
`web/tests/conftest.py` añade `WTF_CSRF_ENABLED=False` al `app.config.update(...)` de la fixture `app`. Con esa única línea las 26 llamadas siguen pasando sin tocarlas.

### Lo que eso deja sin probar
Desactivarlo globalmente significa que la protección no se ejercita nunca. Un archivo nuevo `web/tests/test_csrf.py` construye su propia app **con CSRF activo** (fixture local que no reusa la de `conftest`) y verifica:

1. **POST sin token → 400.** Contra `POST /usuarios/<id>/desactivar`, que muta estado y es de una línea (sin formulario largo que armar).
2. **POST con token válido → no es rechazado.** El token se extrae del HTML de `GET /usuarios` (la lista trae el formulario de desactivar), que es como lo obtiene un navegador real.
3. **La acción no ocurrió cuando se rechazó.** Con el POST sin token, verificar que el `api_client` de desactivar **no fue llamado** (monkeypatch con un espía). El código de estado por sí solo no prueba que no se haya mutado nada.

El punto 3 es el que da valor real: un test que solo mira el 400 pasaría aunque la petición se hubiera ejecutado antes de rechazarse.

## Fuera de alcance

- `SESSION_COOKIE_SAMESITE` y `SESSION_COOKIE_SECURE`.
- CSRF en la API (stateless con JWT en header; no aplica).
- Migrar los formularios a clases `FlaskForm` de WTForms: el panel construye sus formularios a mano en las plantillas y ese refactor es mucho mayor que este slice.
- Rotación del token por petición o límites de tiempo distintos del que trae `flask-wtf` por defecto.
