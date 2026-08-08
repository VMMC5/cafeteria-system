# CSRF en el panel web — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** El panel Flask deja de aceptar POST forjados desde otro sitio: toda ruta que muta estado exige un token CSRF ligado a la sesión.

**Architecture:** `Flask-WTF` con `CSRFProtect` inicializado en el factory protege las 14 rutas POST sin decorar ninguna. Cada uno de los 10 formularios lleva un campo oculto con el token. Un manejador de `CSRFError` convierte el rechazo en una página con explicación devolviendo 400, en vez de la página cruda de Flask. Los tests existentes desactivan la validación con una línea en su fixture; un archivo nuevo la activa a propósito para probar la protección de verdad.

**Tech Stack:** Flask 3.1.3 + Flask-Login + Jinja2 + pytest. El panel consume la API por HTTP; sus tests mockean `api_client` con `monkeypatch`.

**Spec:** `docs/superpowers/specs/2026-08-08-csrf-panel-web-design.md`

## Global Constraints

- **Solo `web/`.** La API no se toca: es stateless y autentica con JWT en el header `Authorization`, así que CSRF no aplica ahí.
- **Versiones exactas** (verificadas como disponibles desde el contenedor): `Flask-WTF==1.3.0` y `WTForms==3.2.2`. El archivo pinea también las transitivas, así que ambas van explícitas.
- **Hay que reconstruir la imagen web** tras tocar `requirements.txt`: `docker compose build web && docker compose up -d web`. Reiniciar el contenedor no basta.
- **Marcado exacto del campo oculto**, idéntico en los 10 formularios (los tests dependen de este orden de atributos):
  `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`
- **El rechazo devuelve 400**, no un redirect: es el código correcto para una petición rechazada y sigue el patrón del panel (`catalogo/routes.py` responde `render_template(...), e.status_code` ante un `ApiError`).
- **No migrar a `FlaskForm`/WTForms.** El panel arma sus formularios a mano en las plantillas; ese refactor es mucho mayor que este slice.
- **Fuera:** `SESSION_COOKIE_SAMESITE`, `SESSION_COOKIE_SECURE`, y rotación o límites de tiempo distintos del default de `flask-wtf`.
- **Commits en español**, formato `tipo(scope): descripción`.
- **Rama:** `feat/web-csrf` (worktree aislado bajo `.claude/worktrees/`).
- **Tests de la web desde un worktree:** el contenedor `web` en marcha monta el checkout **principal**, así que `docker compose exec web pytest` probaría el código equivocado. Usar un contenedor efímero que monte el worktree (ver Task 1 Steps 2 y 3): antes de tocar `requirements.txt` sirve la imagen existente `cafeteria-system-web`; después hay que construir `cafeteria-web-csrf` y usar esa. El `--user 1000:1000` evita que pytest deje `.pytest_cache` como root y bloquee el borrado del worktree.
- **Baseline:** 114 tests de la web en verde antes de empezar.

## Estructura de archivos

| Archivo | Responsabilidad | Acción |
|---|---|---|
| `web/requirements.txt` | Dependencias `Flask-WTF` y `WTForms` | Modificar |
| `web/app/__init__.py` | `CSRFProtect` en el factory + manejador de `CSRFError` | Modificar |
| `web/tests/conftest.py` | `WTF_CSRF_ENABLED=False` en la fixture compartida | Modificar |
| `web/app/templates/auth/login.html` | Token en el formulario de login | Modificar |
| `web/app/templates/usuarios/form.html` | Token | Modificar |
| `web/app/templates/usuarios/list.html` | Token en 2 formularios (dentro del bucle) | Modificar |
| `web/app/templates/catalogo/productos_form.html` | Token | Modificar |
| `web/app/templates/catalogo/productos_list.html` | Token (dentro del bucle) | Modificar |
| `web/app/templates/catalogo/categorias_form.html` | Token | Modificar |
| `web/app/templates/catalogo/categorias_list.html` | Token (dentro del bucle) | Modificar |
| `web/app/templates/catalogo/mesas_form.html` | Token | Modificar |
| `web/app/templates/catalogo/mesas_list.html` | Token (dentro del bucle) | Modificar |
| `web/app/templates/errors/csrf.html` | Página del rechazo | Crear |
| `web/tests/test_csrf.py` | Tests de la protección | Crear |
| `progress.md` | Bitácora | Modificar |

**Orden:** Task 1 (activar + tokens) → Task 2 (manejador + tests de verdad) → Task 3 (verificación + docs).

---

### Task 1: Activar CSRFProtect y poner el token en los 10 formularios

**Files:**
- Modify: `web/requirements.txt`, `web/app/__init__.py`, `web/tests/conftest.py`
- Modify: las 9 plantillas con formulario (ver tabla arriba)
- Test: `web/tests/test_csrf.py` (crear)

**Interfaces:**
- Consumes: nada (primera task).
- Produces: `CSRFProtect` activo en la app; `csrf_token()` disponible en Jinja; la fixture `app` de `conftest.py` con `WTF_CSRF_ENABLED=False`. Task 2 añade tests a `web/tests/test_csrf.py`.

- [ ] **Step 1: Escribir los tests que fallan**

Crear `web/tests/test_csrf.py`. El primer test recorre las plantillas y exige que cada formulario POST lleve su token — cubre los 10 de una vez y atrapa cualquier formulario futuro que nazca sin token. El segundo prueba que el cableado funciona en runtime, no solo el texto de la plantilla:

```python
from pathlib import Path

PLANTILLAS = Path(__file__).resolve().parents[1] / "app" / "templates"


def test_toda_plantilla_con_post_lleva_csrf_token():
    """Cada <form method="post"> debe emitir su propio campo csrf_token.

    Se cuenta por archivo en vez de mirar solo "aparece el token": las listas
    tienen varios formularios y uno solo con token dejaría los demás abiertos.
    """
    faltantes = []
    for archivo in sorted(PLANTILLAS.rglob("*.html")):
        texto = archivo.read_text(encoding="utf-8")
        formularios = texto.count('method="post"')
        if formularios and texto.count("csrf_token") < formularios:
            faltantes.append(archivo.relative_to(PLANTILLAS).as_posix())
    assert faltantes == []


def test_login_renderiza_un_token_real(client):
    """El campo no basta con existir en la plantilla: debe salir con valor."""
    cuerpo = client.get("/login").get_data(as_text=True)
    assert 'name="csrf_token"' in cuerpo
    assert 'value=""' not in cuerpo
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Desde el worktree, el contenedor `web` en marcha monta el checkout **principal**, así que hay que correr los tests contra el código del worktree con un contenedor efímero. En esta fase RED todavía no hace falta `flask-wtf`, así que sirve la imagen que ya existe:

Run: `docker run --rm --user 1000:1000 -v <worktree>/web:/code -w /code cafeteria-system-web pytest tests/test_csrf.py -v`
Expected: FAIL — `test_toda_plantilla_con_post_lleva_csrf_token` lista las 9 plantillas, y `test_login_renderiza_un_token_real` falla porque no existe `csrf_token` en el HTML.

- [ ] **Step 3: Añadir las dependencias y construir una imagen propia**

En `web/requirements.txt`, añadir en orden alfabético junto a las demás:

```
Flask-WTF==1.3.0
WTForms==3.2.2
```

Las dependencias viven dentro de la imagen, así que hay que construir una. **No usar `docker compose build web` desde el worktree**: el nombre del proyecto sale del directorio, así que produciría una imagen llamada `feat-web-csrf-web` y además podría pisar la del checkout principal. Construir una imagen propia con nombre explícito:

```bash
docker build -t cafeteria-web-csrf <worktree>/web
```

De aquí en adelante los tests corren con esa imagen. El montaje `-v <worktree>/web:/code` sobrescribe el código copiado en la imagen, así que basta con reconstruirla cuando cambien las dependencias, no en cada edición.

- [ ] **Step 4: Inicializar CSRFProtect en el factory**

En `web/app/__init__.py`, añadir el import y la instancia a nivel de módulo junto a `login_manager`:

```python
from flask_wtf.csrf import CSRFProtect

login_manager = LoginManager()
login_manager.login_view = "auth.login"
csrf = CSRFProtect()
```

Y dentro de `create_app`, inicializarlo justo después de `login_manager.init_app(app)`:

```python
    login_manager.init_app(app)
    csrf.init_app(app)
```

- [ ] **Step 5: Desactivar la validación en la fixture de tests**

En `web/tests/conftest.py`, la fixture `app` pasa a:

```python
@pytest.fixture()
def app():
    app = create_app()
    # Los 26 client.post del suite no mandan token; la protección se prueba
    # a propósito en test_csrf.py, que levanta su propia app con CSRF activo.
    app.config.update(TESTING=True, SECRET_KEY="test", WTF_CSRF_ENABLED=False)
    return app
```

- [ ] **Step 6: Poner el token en los 10 formularios**

En cada uno, como primer elemento dentro del `<form>`, con este marcado exacto:

```html
<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
```

Archivos y ubicación:
- `auth/login.html` — dentro del `<form>` de la línea 21.
- `usuarios/form.html` — dentro del `<form>` de la línea 11.
- `usuarios/list.html` — **dos**: en el formulario de `usuarios.desactivar` (línea 52) y en el de `usuarios.activar` (línea 57). Ambos están dentro del bucle de usuarios, así que el token queda dentro del `for` y cada fila emite el suyo.
- `catalogo/productos_form.html` — línea 11.
- `catalogo/productos_list.html` — formulario de `catalogo.producto_toggle` (línea 43), dentro del bucle.
- `catalogo/categorias_form.html` — línea 11.
- `catalogo/categorias_list.html` — formulario de `catalogo.categoria_eliminar` (línea 27), dentro del bucle.
- `catalogo/mesas_form.html` — línea 11.
- `catalogo/mesas_list.html` — formulario de `catalogo.mesa_eliminar` (línea 30), dentro del bucle.

Los formularios de las listas abren en varias líneas (`<form method="post" action="..."` y en la siguiente el `onsubmit=...`), así que el campo va **después** del `>` que cierra la etiqueta de apertura, no en medio de sus atributos.

- [ ] **Step 7: Correr los tests nuevos y verificar que pasan**

Run: `docker run --rm --user 1000:1000 -v <worktree>/web:/code -w /code cafeteria-web-csrf pytest tests/test_csrf.py -v`
Expected: PASS — 2 tests.

- [ ] **Step 8: Correr la suite completa de la web (no regresión)**

Run: `docker run --rm --user 1000:1000 -v <worktree>/web:/code -w /code cafeteria-web-csrf pytest -q`
Expected: PASS — 114 previos + 2 nuevos = **116**. Si alguno de los 114 falla, PARAR: significa que la fixture no está desactivando la validación donde debía.

- [ ] **Step 9: Commit**

```bash
git add web/requirements.txt web/app/__init__.py web/tests/conftest.py web/tests/test_csrf.py web/app/templates
git commit -m "feat(web): protección CSRF con Flask-WTF y token en los formularios"
```

---

### Task 2: Manejador de CSRFError y tests que sí ejercitan la protección

**Files:**
- Modify: `web/app/__init__.py`
- Create: `web/app/templates/errors/csrf.html`
- Test: `web/tests/test_csrf.py`

**Interfaces:**
- Consumes: `CSRFProtect` activo y `csrf_token()` en las plantillas (Task 1).
- Produces: página de rechazo con status 400; fixtures locales `csrf_app` / `csrf_client` para una app con CSRF activo.

- [ ] **Step 1: Escribir los tests que fallan**

Añadir a `web/tests/test_csrf.py`. Estos usan **fixtures propias** con la validación activa, porque la fixture `app` de `conftest.py` la desactiva.

Los cuatro imports nuevos (`re`, `pytest`, `create_app`, `api_client`) van **arriba, junto al `from pathlib import Path` que ya está**, no al final del archivo. Las constantes y funciones siguen después:

```python
import re

import pytest

from app import create_app
from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
USUARIOS = [
    {"id_usuario": 2, "nombre": "Ana", "apellido_paterno": "Prueba",
     "correo": "ana@x.com", "activo": True, "rol": {"nombre_rol": "Mesero"}},
]


@pytest.fixture()
def csrf_client():
    app = create_app()
    app.config.update(TESTING=True, SECRET_KEY="test", WTF_CSRF_ENABLED=True)
    return app.test_client()


def _token(html: str) -> str:
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "no se encontró el campo csrf_token en el HTML"
    return m.group(1)


def _login(client, monkeypatch):
    """Inicia sesión respetando CSRF: toma el token del formulario de login."""
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    token = _token(client.get("/login").get_data(as_text=True))
    r = client.post("/login", data={
        "correo": "admin@cafeteria.com", "password": "secret123", "csrf_token": token,
    })
    assert r.status_code == 302, "el login con token válido no debería ser rechazado"


def test_post_sin_token_es_rechazado_con_400(csrf_client, monkeypatch):
    _login(csrf_client, monkeypatch)
    r = csrf_client.post("/usuarios/2/desactivar")
    assert r.status_code == 400
    assert "sesión" in r.get_data(as_text=True).lower()


def test_post_sin_token_no_ejecuta_la_accion(csrf_client, monkeypatch):
    """El 400 por sí solo no prueba nada: hay que ver que no se mutó."""
    _login(csrf_client, monkeypatch)
    llamadas = []
    monkeypatch.setattr(
        api_client, "delete_usuario", lambda a, i: llamadas.append(i)
    )
    csrf_client.post("/usuarios/2/desactivar")
    assert llamadas == []


def test_post_con_token_valido_pasa(csrf_client, monkeypatch):
    _login(csrf_client, monkeypatch)
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: USUARIOS)
    llamadas = []
    monkeypatch.setattr(
        api_client, "delete_usuario", lambda a, i: llamadas.append(i)
    )
    token = _token(csrf_client.get("/usuarios").get_data(as_text=True))
    r = csrf_client.post("/usuarios/2/desactivar", data={"csrf_token": token})
    assert r.status_code == 302
    assert llamadas == [2]
```

- [ ] **Step 2: Correr los tests y verificar que fallan**

Run: `docker run --rm --user 1000:1000 -v <worktree>/web:/code -w /code cafeteria-web-csrf pytest tests/test_csrf.py -v`
Expected: FAIL en `test_post_sin_token_es_rechazado_con_400` — devuelve 400 pero con la página por defecto de Flask, que no contiene la palabra "sesión". Los otros dos ya deberían pasar: prueban la protección, que Task 1 dejó activa.

- [ ] **Step 3: Crear la plantilla de la página de rechazo**

Crear `web/app/templates/errors/csrf.html`:

```html
{% extends "base.html" %}
{% block title %}Sesión expirada · Cafetería Aroma{% endblock %}
{% block content %}
<section class="card">
  <h1>La sesión del formulario expiró</h1>
  <p>
    Por seguridad, los formularios del panel caducan tras un rato sin usarse.
    No se realizó ningún cambio: vuelve a abrir el formulario e inténtalo de nuevo.
  </p>
  <p><a class="btn" href="{{ url_for('dashboard.index') }}">Volver al inicio</a></p>
</section>
{% endblock %}
```

- [ ] **Step 4: Registrar el manejador en el factory**

En `web/app/__init__.py`, ampliar el import de `flask` para incluir `render_template` y añadir el import de `CSRFError`:

```python
from flask import Flask, redirect, render_template, url_for
from flask_wtf.csrf import CSRFError, CSRFProtect
```

Y registrar el manejador dentro de `create_app`, junto al de `ReloginRequired`:

```python
    @app.errorhandler(CSRFError)
    def _csrf_error(_e):
        return render_template("errors/csrf.html"), 400
```

- [ ] **Step 5: Correr los tests y verificar que pasan**

Run: `docker run --rm --user 1000:1000 -v <worktree>/web:/code -w /code cafeteria-web-csrf pytest tests/test_csrf.py -v`
Expected: PASS — 5 tests (los 2 de Task 1 + los 3 nuevos).

- [ ] **Step 6: Correr la suite completa**

Run: `docker run --rm --user 1000:1000 -v <worktree>/web:/code -w /code cafeteria-web-csrf pytest -q`
Expected: PASS — **119** (114 previos + 2 de Task 1 + 3 de Task 2). Reportar el número real observado.

- [ ] **Step 7: Commit**

```bash
git add web/app/__init__.py web/app/templates/errors/csrf.html web/tests/test_csrf.py
git commit -m "feat(web): página de rechazo CSRF con status 400 y tests de la protección"
```

---

### Task 3: Verificación integral y documentación

**Files:**
- Modify: `progress.md`

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: bitácora actualizada; rama lista para PR.

- [ ] **Step 1: Suite completa de la web**

Run: `docker run --rm --user 1000:1000 -v <worktree>/web:/code -w /code cafeteria-web-csrf pytest -q`
Expected: 119 tests (114 previos + 5 nuevos), sin fallos. Reportar el número real.

- [ ] **Step 2: Suite del backend (no debe haberse tocado)**

Run: `docker compose exec api pytest -q`
Expected: 217 tests. Este slice no toca `backend/`; si algo cambió ahí, es un error.

- [ ] **Step 3: Smoke manual del panel**

Levantar la web con el código de la rama y recorrerla:

```bash
docker compose build web && docker compose up -d web
```

Verificar en el navegador (`localhost:5000`, `admin@cafeteria.com` / `cafeteria123`):
1. El login funciona.
2. Crear y editar un producto, una categoría y una mesa.
3. Desactivar y reactivar un usuario.
4. Eliminar una categoría y una mesa.
5. Alternar la disponibilidad de un producto.
6. Ver el código fuente de una página: los formularios traen `name="csrf_token"` con valor.

Cualquier acción que devuelva la página de "sesión expirada" en un flujo normal significa que a ese formulario le falta el token.

- [ ] **Step 4: Actualizar `progress.md`**

En "Deuda técnica / mejoras conocidas", reemplazar la mención al CSRF como pendiente por una línea que registre la protección activa: `CSRFProtect` global, token en los 10 formularios, rechazo con página propia y 400, y que los tests del panel desactivan la validación salvo `test_csrf.py`, que la activa a propósito.

En "Próximo", registrar que con esto quedan cerrados **los dos** diferidos del review del PR #21 (guard de Ocupada en el PR #24 y CSRF aquí), y dejar como candidato siguiente el camino de "cerrar sin cobro" para el pedido entregado que nadie paga. Actualizar la cabecera "Última actualización".

- [ ] **Step 5: Commit**

```bash
git add progress.md
git commit -m "docs: progress.md — protección CSRF en el panel web"
```

- [ ] **Step 6: Abrir el PR**

```bash
git push -u origin feat/web-csrf
gh pr create --base main \
  --title "feat(web): protección CSRF en el panel de administración" \
  --body "$(cat <<'EOF'
## Resumen

Cierra el último diferido del review del PR #21: el panel Flask no tenía ninguna protección CSRF — `flask-wtf` ni siquiera estaba instalado. Como la sesión viaja en cookie y se envía sola, cualquier página externa podía hacer que el navegador de un administrador autenticado disparara un POST al panel: crear o desactivar usuarios, borrar mesas y categorías, o alternar la disponibilidad de productos.

- **`CSRFProtect` global** en el factory: cubre las 14 rutas POST sin decorar ninguna.
- **Token en los 10 formularios** de las 9 plantillas; los 4 que viven dentro de bucles lo emiten por fila.
- **Página propia para el rechazo** con status 400 (no un redirect: es el código correcto y sigue el patrón del panel ante un `ApiError`). El token caduca a la hora, así que un formulario abierto en otra pestaña produce este caso en uso normal.
- **Los tests del panel desactivan la validación** con una línea en su fixture, y `test_csrf.py` levanta su propia app **con CSRF activo** para probarla de verdad: rechazo sin token, aceptación con token tomado del HTML, y —lo que importa— que la acción **no se ejecutó** cuando fue rechazada.
- Un test recorre todas las plantillas y exige un `csrf_token` por cada `method="post"`, así que un formulario futuro sin token rompe la suite.

La API no necesita CSRF: es stateless y autentica con JWT en el header `Authorization`, que un formulario cross-site no puede fijar.

## Test plan

- [x] Web: 119 tests (114 previos + 5 nuevos)
- [x] Backend: 217 tests — este slice no toca `backend/`
- [x] Smoke manual del panel: login, CRUD de productos/categorías/mesas, activar y desactivar usuario, eliminar, toggle

## Nota de despliegue

`requirements.txt` cambió, así que hay que **reconstruir la imagen**: `docker compose build web && docker compose up -d web`. Reiniciar el contenedor no basta.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```
