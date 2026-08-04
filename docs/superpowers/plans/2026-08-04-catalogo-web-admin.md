# CRUD de Catálogo en la Web Admin — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Gestionar productos, categorías y mesas desde el panel Flask (`/catalogo` con pestañas), consumiendo el CRUD que la API ya expone.

**Architecture:** Un blueprint `catalogo` con 3 sub-recursos server-rendered, calcado del patrón `usuarios` (rutas `@login_required` → `api_gateway.call(api_client.<fn>, ...)` → flash + redirect/re-render). 14 funciones nuevas en `api_client.py`. Sin cambios en `backend/`.

**Tech Stack:** Flask + Jinja2 + flask-login (web), requests hacia la API FastAPI, pytest con `monkeypatch` sobre `api_client`.

**Spec:** `docs/superpowers/specs/2026-08-04-catalogo-web-admin-design.md`

## Global Constraints

- **Solo `web/`** — prohibido tocar `backend/` (la API ya soporta todo).
- **Decimal como string:** la API serializa `Decimal` como string JSON (`"45.00"`). Se interpola tal cual en templates (`$ {{ p.precio_venta }}`), nunca `float()`; los stubs de test usan strings (`"45.00"`), no floats.
- **JS inline:** no declarar globales reservados (`top`, `name`, `parent`, …). Esta rebanada no añade JS nuevo (solo `confirm()` inline en `onsubmit`).
- **Tests:** correr con `docker compose exec web pytest <ruta> -v` (requiere `docker compose up -d` previo). Fallback local: `cd web && .venv/bin/python -m pytest <ruta> -v`.
- **Hot-reload:** tras registrar el blueprint, `docker compose restart web` (el reloader no recarga registro de rutas).
- **UI en español**, tema "Cafetería Aroma"; reutilizar clases CSS existentes (`.table`, `.card`, `.toolbar`, `.badge--on/off`, `.page-head`, `.btn`, `.icon-btn`, `.link-danger`, `.link-ok`).
- **Commits atómicos** por tarea, estilo del historial: `feat(web): …` / `test(web): …`.
- Trabajar en rama `feat/web-catalogo` (el worktree/rama la crea la skill de ejecución al inicio).

---

### Task 1: Funciones de catálogo en `api_client`

**Files:**
- Modify: `web/app/services/api_client.py` (append al final)
- Test: `web/tests/test_api_client.py` (append al final)

**Interfaces:**
- Consumes: helpers existentes `_base()`, `_headers()`, `_check()`, `_detail()`, `ApiError`, `TIMEOUT`.
- Produces (las tareas 2–4 llaman exactamente estas firmas; todas reciben `access` como primer arg porque `api_gateway.call` lo inyecta):
  - `list_productos(access, id_categoria=None, disponible=None)`, `get_producto(access, id_producto)`, `create_producto(access, payload)`, `update_producto(access, id_producto, payload)`
  - `list_categorias(access)`, `get_categoria(access, id_categoria)`, `create_categoria(access, payload)`, `update_categoria(access, id_categoria, payload)`, `delete_categoria(access, id_categoria)` → `None`
  - `list_mesas(access)`, `get_mesa(access, id_mesa)`, `create_mesa(access, payload)`, `update_mesa(access, id_mesa, payload)`, `delete_mesa(access, id_mesa)` → `None`

**Nota clave:** el DELETE de la API para mesas/categorías responde **204 sin cuerpo**; `_check()` siempre hace `resp.json()` y explotaría. Los deletes usan un helper propio `_check_no_content()`.

- [ ] **Step 1: Escribir los tests que fallan** — append a `web/tests/test_api_client.py`:

```python
def test_list_productos_filtra_params(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers")
        captured["params"] = kwargs.get("params")
        return _Resp(200, [{"id_producto": 1, "precio_venta": "45.00"}])

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    out = api_client.list_productos("tok", id_categoria=2, disponible=True)
    assert out[0]["precio_venta"] == "45.00"
    assert captured["url"].endswith("/productos")
    assert captured["headers"]["Authorization"] == "Bearer tok"
    assert captured["params"] == {"id_categoria": 2, "disponible": True}


def test_list_productos_sin_filtros_no_manda_params(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["params"] = kwargs.get("params")
        return _Resp(200, [])

    monkeypatch.setattr(api_client.requests, "get", fake_get)
    api_client.list_productos("tok")
    assert captured["params"] is None


def test_create_producto_postea_json(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["json"] = kwargs.get("json")
        return _Resp(201, {"id_producto": 7})

    monkeypatch.setattr(api_client.requests, "post", fake_post)
    out = api_client.create_producto(
        "tok", {"nombre_producto": "Latte", "precio_venta": "45.00"}
    )
    assert out == {"id_producto": 7}
    assert captured["url"].endswith("/productos")
    assert captured["json"]["precio_venta"] == "45.00"


def test_delete_mesa_204_devuelve_none(monkeypatch):
    captured = {}

    def fake_delete(url, **kwargs):
        captured["url"] = url
        return _Resp(204)

    monkeypatch.setattr(api_client.requests, "delete", fake_delete)
    assert api_client.delete_mesa("tok", 3) is None
    assert captured["url"].endswith("/mesas/3")


def test_delete_categoria_con_referencias_lanza_apierror(monkeypatch):
    monkeypatch.setattr(
        api_client.requests, "delete",
        lambda url, **k: _Resp(409, {"detail": "La categoría tiene productos"}),
    )
    with pytest.raises(ApiError) as exc:
        api_client.delete_categoria("tok", 2)
    assert exc.value.status_code == 409
```

- [ ] **Step 2: Verificar que fallan**

Run: `docker compose exec web pytest tests/test_api_client.py -v`
Expected: FAIL los 5 nuevos con `AttributeError: ... has no attribute 'list_productos'` (etc.); los 3 previos PASS.

- [ ] **Step 3: Implementar** — append a `web/app/services/api_client.py`:

```python
# --- Catálogo ---

def _check_no_content(resp):
    """DELETE de catálogo: 204 sin cuerpo en éxito; error JSON en fallo."""
    if resp.status_code >= 400:
        raise ApiError(resp.status_code, _detail(resp))
    return None


def list_productos(access, id_categoria=None, disponible=None):
    params = {}
    if id_categoria is not None:
        params["id_categoria"] = id_categoria
    if disponible is not None:
        params["disponible"] = disponible
    r = requests.get(
        f"{_base()}/productos", headers=_headers(access),
        params=params or None, timeout=TIMEOUT,
    )
    return _check(r)


def get_producto(access, id_producto):
    r = requests.get(
        f"{_base()}/productos/{id_producto}", headers=_headers(access), timeout=TIMEOUT
    )
    return _check(r)


def create_producto(access, payload):
    r = requests.post(
        f"{_base()}/productos", headers=_headers(access), json=payload, timeout=TIMEOUT
    )
    return _check(r, ok=None)


def update_producto(access, id_producto, payload):
    r = requests.patch(
        f"{_base()}/productos/{id_producto}",
        headers=_headers(access), json=payload, timeout=TIMEOUT,
    )
    return _check(r, ok=None)


def list_categorias(access):
    r = requests.get(f"{_base()}/categorias", headers=_headers(access), timeout=TIMEOUT)
    return _check(r)


def get_categoria(access, id_categoria):
    r = requests.get(
        f"{_base()}/categorias/{id_categoria}", headers=_headers(access), timeout=TIMEOUT
    )
    return _check(r)


def create_categoria(access, payload):
    r = requests.post(
        f"{_base()}/categorias", headers=_headers(access), json=payload, timeout=TIMEOUT
    )
    return _check(r, ok=None)


def update_categoria(access, id_categoria, payload):
    r = requests.patch(
        f"{_base()}/categorias/{id_categoria}",
        headers=_headers(access), json=payload, timeout=TIMEOUT,
    )
    return _check(r, ok=None)


def delete_categoria(access, id_categoria):
    r = requests.delete(
        f"{_base()}/categorias/{id_categoria}", headers=_headers(access), timeout=TIMEOUT
    )
    return _check_no_content(r)


def list_mesas(access):
    r = requests.get(f"{_base()}/mesas", headers=_headers(access), timeout=TIMEOUT)
    return _check(r)


def get_mesa(access, id_mesa):
    r = requests.get(
        f"{_base()}/mesas/{id_mesa}", headers=_headers(access), timeout=TIMEOUT
    )
    return _check(r)


def create_mesa(access, payload):
    r = requests.post(
        f"{_base()}/mesas", headers=_headers(access), json=payload, timeout=TIMEOUT
    )
    return _check(r, ok=None)


def update_mesa(access, id_mesa, payload):
    r = requests.patch(
        f"{_base()}/mesas/{id_mesa}",
        headers=_headers(access), json=payload, timeout=TIMEOUT,
    )
    return _check(r, ok=None)


def delete_mesa(access, id_mesa):
    r = requests.delete(
        f"{_base()}/mesas/{id_mesa}", headers=_headers(access), timeout=TIMEOUT
    )
    return _check_no_content(r)
```

- [ ] **Step 4: Verificar que pasan**

Run: `docker compose exec web pytest tests/test_api_client.py -v`
Expected: PASS todos (8).

- [ ] **Step 5: Commit**

```bash
git add web/app/services/api_client.py web/tests/test_api_client.py
git commit -m "feat(web): funciones de catálogo (productos/categorías/mesas) en api_client"
```

---

### Task 2: Blueprint `catalogo` + sub-recurso Productos + sidebar

**Files:**
- Create: `web/app/catalogo/__init__.py` (vacío), `web/app/catalogo/routes.py`
- Create: `web/app/templates/catalogo/_tabs.html`, `web/app/templates/catalogo/productos_list.html`, `web/app/templates/catalogo/productos_form.html`
- Modify: `web/app/__init__.py` (registro), `web/app/templates/base.html` (ítem sidebar), `web/app/static/css/app.css` (append estilos `.tabs`)
- Test: `web/tests/test_catalogo.py` (nuevo)

**Interfaces:**
- Consumes: de Task 1 — `list_productos(access, id_categoria=None, disponible=None)`, `get_producto`, `create_producto`, `update_producto`, `list_categorias`.
- Produces: blueprint `catalogo` (url_prefix `/catalogo`) con endpoints `catalogo.index`, `catalogo.productos`, `catalogo.producto_nuevo`, `catalogo.producto_crear`, `catalogo.producto_editar`, `catalogo.producto_actualizar`, `catalogo.producto_toggle`. Template parcial `_tabs.html` que espera la variable Jinja `tab`. Los stubs `ADMIN_TOKENS`/`ADMIN_ME`/`_login`/`CATEGORIAS`/`PRODUCTOS` de `test_catalogo.py` los reutilizan las tareas 3–4.

- [ ] **Step 1: Escribir los tests que fallan** — crear `web/tests/test_catalogo.py`:

```python
from app.services import api_client

ADMIN_TOKENS = {"access_token": "a", "refresh_token": "r", "token_type": "bearer"}
ADMIN_ME = {
    "id_usuario": 1, "nombre": "Admin", "apellido_paterno": "Sistema",
    "apellido_materno": None, "correo": "admin@cafeteria.com",
    "nombre_usuario": "admin", "id_rol": 1, "activo": True,
    "fecha_registro": "2026-07-04T00:00:00Z",
    "rol": {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
}
CATEGORIAS = [
    {"id_categoria": 1, "nombre_categoria": "Bebidas calientes", "descripcion": None},
    {"id_categoria": 2, "nombre_categoria": "Postres", "descripcion": "Dulces"},
]
# Decimal viaja como string en JSON: los stubs usan strings, no floats.
PRODUCTOS = [
    {"id_producto": 1, "id_categoria": 1, "nombre_producto": "Latte",
     "descripcion": None, "precio_venta": "45.00", "disponible": True,
     "fecha_registro": "2026-07-04T00:00:00Z", "categoria": CATEGORIAS[0]},
    {"id_producto": 2, "id_categoria": 2, "nombre_producto": "Brownie",
     "descripcion": "Con nuez", "precio_venta": "35.50", "disponible": False,
     "fecha_registro": "2026-07-04T00:00:00Z", "categoria": CATEGORIAS[1]},
]


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "secret123"})


def test_catalogo_sin_sesion_redirige_a_login(client):
    r = client.get("/catalogo/productos")
    assert r.status_code == 302
    assert "/login" in r.headers["Location"]


def test_catalogo_redirige_a_productos(client, monkeypatch):
    _login(client, monkeypatch)
    r = client.get("/catalogo")
    assert r.status_code == 302
    assert "/catalogo/productos" in r.headers["Location"]


def test_lista_productos_renderiza_precio_string(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_productos", lambda a, c=None, d=None: PRODUCTOS)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    cuerpo = client.get("/catalogo/productos").get_data(as_text=True)
    assert "Latte" in cuerpo
    assert "$ 45.00" in cuerpo
    assert "No disponible" in cuerpo  # Brownie está inactivo


def test_lista_productos_pasa_filtros_a_la_api(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_list(access, id_categoria=None, disponible=None):
        llamado["id_categoria"] = id_categoria
        llamado["disponible"] = disponible
        return []

    monkeypatch.setattr(api_client, "list_productos", fake_list)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    client.get("/catalogo/productos?categoria=2&disponible=0")
    assert llamado == {"id_categoria": 2, "disponible": False}


def test_crear_producto_ok_redirige(client, monkeypatch):
    _login(client, monkeypatch)
    capturado = {}

    def fake_create(access, payload):
        capturado["payload"] = payload
        return {"id_producto": 9, **payload}

    monkeypatch.setattr(api_client, "create_producto", fake_create)
    r = client.post("/catalogo/productos", data={
        "nombre_producto": "Capuchino", "descripcion": "",
        "id_categoria": "1", "precio_venta": "52.00", "disponible": "on",
    })
    assert r.status_code == 302
    assert "/catalogo/productos" in r.headers["Location"]
    # precio viaja como string tal cual (Pydantic Decimal lo acepta)
    assert capturado["payload"] == {
        "nombre_producto": "Capuchino", "descripcion": None,
        "id_categoria": 1, "precio_venta": "52.00", "disponible": True,
    }


def test_crear_producto_error_api_rerenderiza(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_create(access, payload):
        raise ApiError(422, "precio_venta inválido")

    monkeypatch.setattr(api_client, "create_producto", fake_create)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    r = client.post("/catalogo/productos", data={
        "nombre_producto": "X", "descripcion": "", "id_categoria": "1",
        "precio_venta": "-1", "disponible": "on",
    })
    assert r.status_code == 422
    assert "inválido" in r.get_data(as_text=True)


def test_form_editar_producto_precarga(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "get_producto", lambda a, i: PRODUCTOS[0])
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    cuerpo = client.get("/catalogo/productos/1/editar").get_data(as_text=True)
    assert 'value="Latte"' in cuerpo
    assert 'value="45.00"' in cuerpo


def test_toggle_producto_manda_negacion(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_update(access, id_producto, payload):
        llamado["id"] = id_producto
        llamado["payload"] = payload
        return {"id_producto": id_producto, **payload}

    monkeypatch.setattr(api_client, "update_producto", fake_update)
    # Brownie está en disponible=False; la lista manda el valor destino "1"
    r = client.post("/catalogo/productos/2/toggle", data={"disponible": "1"})
    assert r.status_code == 302
    assert llamado == {"id": 2, "payload": {"disponible": True}}


def test_sidebar_muestra_catalogo(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_productos", lambda a, c=None, d=None: [])
    monkeypatch.setattr(api_client, "list_categorias", lambda a: [])
    cuerpo = client.get("/catalogo/productos").get_data(as_text=True)
    assert "Catálogo" in cuerpo
```

- [ ] **Step 2: Verificar que fallan**

Run: `docker compose exec web pytest tests/test_catalogo.py -v`
Expected: FAIL todos con 404 (`/catalogo/*` no existe) — los asserts de 302/200 no se cumplen.

- [ ] **Step 3: Implementar el blueprint** — crear `web/app/catalogo/__init__.py` **vacío** y `web/app/catalogo/routes.py`:

```python
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.services import api_client, api_gateway
from app.services.api_client import ApiError

bp = Blueprint("catalogo", __name__, url_prefix="/catalogo")


def _payload_producto(form):
    return {
        "nombre_producto": form["nombre_producto"].strip(),
        "descripcion": (form.get("descripcion") or "").strip() or None,
        "id_categoria": int(form["id_categoria"]),
        "precio_venta": form["precio_venta"],
        "disponible": form.get("disponible") == "on",
    }


@bp.route("")
@login_required
def index():
    return redirect(url_for("catalogo.productos"))


@bp.route("/productos")
@login_required
def productos():
    cat = request.args.get("categoria") or ""
    disp = request.args.get("disponible") or ""
    id_categoria = int(cat) if cat else None
    disponible = None if disp == "" else disp == "1"
    items = api_gateway.call(api_client.list_productos, id_categoria, disponible)
    categorias = api_gateway.call(api_client.list_categorias)
    return render_template(
        "catalogo/productos_list.html",
        productos=items, categorias=categorias, categoria=cat, disponible=disp,
    )


@bp.route("/productos/nuevo")
@login_required
def producto_nuevo():
    categorias = api_gateway.call(api_client.list_categorias)
    return render_template(
        "catalogo/productos_form.html",
        categorias=categorias, producto=None, form={"disponible": True},
    )


@bp.route("/productos", methods=["POST"])
@login_required
def producto_crear():
    try:
        api_gateway.call(api_client.create_producto, _payload_producto(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        categorias = api_gateway.call(api_client.list_categorias)
        return (
            render_template(
                "catalogo/productos_form.html",
                categorias=categorias, producto=None, form=request.form,
            ),
            e.status_code,
        )
    flash("Producto creado.", "info")
    return redirect(url_for("catalogo.productos"))


@bp.route("/productos/<int:id_producto>/editar")
@login_required
def producto_editar(id_producto):
    producto = api_gateway.call(api_client.get_producto, id_producto)
    categorias = api_gateway.call(api_client.list_categorias)
    return render_template(
        "catalogo/productos_form.html",
        categorias=categorias, producto=producto, form=producto,
    )


@bp.route("/productos/<int:id_producto>", methods=["POST"])
@login_required
def producto_actualizar(id_producto):
    try:
        api_gateway.call(
            api_client.update_producto, id_producto, _payload_producto(request.form)
        )
    except ApiError as e:
        flash(e.detail, "error")
        producto = api_gateway.call(api_client.get_producto, id_producto)
        categorias = api_gateway.call(api_client.list_categorias)
        return (
            render_template(
                "catalogo/productos_form.html",
                categorias=categorias, producto=producto, form=request.form,
            ),
            e.status_code,
        )
    flash("Producto actualizado.", "info")
    return redirect(url_for("catalogo.productos"))


@bp.route("/productos/<int:id_producto>/toggle", methods=["POST"])
@login_required
def producto_toggle(id_producto):
    disponible = request.form.get("disponible") == "1"
    try:
        api_gateway.call(api_client.update_producto, id_producto, {"disponible": disponible})
        flash("Producto actualizado.", "info")
    except ApiError as e:
        flash(e.detail, "error")
    return redirect(url_for("catalogo.productos"))
```

- [ ] **Step 4: Registrar el blueprint** — en `web/app/__init__.py`, dentro de `create_app()`, junto a los imports de blueprints existentes:

```python
from app.catalogo.routes import bp as catalogo_bp
```

y junto a los `register_blueprint` existentes:

```python
app.register_blueprint(catalogo_bp)
```

- [ ] **Step 5: Templates** — crear `web/app/templates/catalogo/_tabs.html` (las tareas 3 y 4 añaden su pestaña aquí):

```html
<nav class="tabs">
  <a class="tab {{ 'active' if tab == 'productos' }}" href="{{ url_for('catalogo.productos') }}">Productos</a>
</nav>
```

Crear `web/app/templates/catalogo/productos_list.html`:

```html
{% extends "base.html" %}
{% block title %}Catálogo · Productos — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>Catálogo</h1>
    <p class="sub">{{ productos|length }} producto(s)</p>
  </div>
  <a class="btn btn--accent" href="{{ url_for('catalogo.producto_nuevo') }}">+ Nuevo producto</a>
</div>

{% set tab = 'productos' %}
{% include "catalogo/_tabs.html" %}

<form method="get" class="toolbar">
  <select name="categoria" onchange="this.form.submit()">
    <option value="">Categoría: Todas</option>
    {% for c in categorias %}
    <option value="{{ c.id_categoria }}" {{ 'selected' if categoria == c.id_categoria|string }}>{{ c.nombre_categoria }}</option>
    {% endfor %}
  </select>
  <select name="disponible" onchange="this.form.submit()">
    <option value="">Estado: Todos</option>
    <option value="1" {{ 'selected' if disponible == '1' }}>Disponible</option>
    <option value="0" {{ 'selected' if disponible == '0' }}>No disponible</option>
  </select>
</form>

<div class="card" style="padding:0;overflow:hidden;">
<table class="table">
  <thead>
    <tr><th>Producto</th><th>Categoría</th><th>Precio</th><th>Estado</th><th></th></tr>
  </thead>
  <tbody>
  {% for p in productos %}
    <tr>
      <td>{{ p.nombre_producto }}{% if p.descripcion %}<br><small>{{ p.descripcion }}</small>{% endif %}</td>
      <td>{{ p.categoria.nombre_categoria }}</td>
      <td>$ {{ p.precio_venta }}</td>
      <td><span class="badge badge--{{ 'on' if p.disponible else 'off' }}">{{ 'Disponible' if p.disponible else 'No disponible' }}</span></td>
      <td class="actions">
        <a class="icon-btn" href="{{ url_for('catalogo.producto_editar', id_producto=p.id_producto) }}" title="Editar">✎</a>
        <form method="post" action="{{ url_for('catalogo.producto_toggle', id_producto=p.id_producto) }}">
          <input type="hidden" name="disponible" value="{{ '0' if p.disponible else '1' }}">
          {% if p.disponible %}
          <button class="link-danger" type="submit" title="Desactivar">Desactivar</button>
          {% else %}
          <button class="link-ok" type="submit" title="Activar">Activar</button>
          {% endif %}
        </form>
      </td>
    </tr>
  {% else %}
    <tr><td colspan="5" class="muted">Sin productos.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
```

Crear `web/app/templates/catalogo/productos_form.html`:

```html
{% extends "base.html" %}
{% block title %}{{ 'Editar' if producto else 'Nuevo' }} producto — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>{{ 'Editar' if producto else 'Nuevo' }} producto</h1>
    <p class="sub">Define el producto del menú y su precio</p>
  </div>
</div>

<form method="post"
      action="{{ url_for('catalogo.producto_actualizar', id_producto=producto.id_producto) if producto else url_for('catalogo.producto_crear') }}">
  <div class="card">
    <h2 class="card__title">Datos del producto</h2>
    <label>Nombre
      <input name="nombre_producto" value="{{ form.get('nombre_producto', '') }}" required></label>
    <label>Descripción
      <input name="descripcion" value="{{ form.get('descripcion', '') or '' }}"></label>
    <label>Categoría
      <select name="id_categoria" required>
        {% for c in categorias %}
        <option value="{{ c.id_categoria }}" {{ 'selected' if form.get('id_categoria')|string == c.id_categoria|string }}>{{ c.nombre_categoria }}</option>
        {% endfor %}
      </select></label>
    <label>Precio de venta ($)
      <input type="number" name="precio_venta" value="{{ form.get('precio_venta', '') }}" step="0.01" min="0" required></label>
    <label class="inline">
      <input type="checkbox" name="disponible" {{ 'checked' if form.get('disponible') in (True, 'on') }}>
      Disponible
    </label>
    <div class="header-row" style="margin-top:1rem;">
      <button type="submit">Guardar producto</button>
      <a class="btn btn--ghost" href="{{ url_for('catalogo.productos') }}">Cancelar</a>
    </div>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 6: Sidebar y CSS** — en `web/app/templates/base.html`, entre el link de Usuarios y el de Reportes, insertar:

```html
      <a class="sidebar__link {{ 'active' if request.endpoint and request.endpoint.startswith('catalogo.') }}" href="{{ url_for('catalogo.productos') }}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h7"/><circle cx="17.5" cy="17.5" r="3"/></svg>
        Catálogo
      </a>
```

Append al final de `web/app/static/css/app.css`:

```css
/* Pestañas del catálogo */
.tabs { display:flex; gap:.25rem; margin-bottom:1rem; border-bottom:1px solid var(--border); }
.tab { padding:.55rem .9rem; color:var(--muted); text-decoration:none; font-weight:600; border-bottom:2px solid transparent; margin-bottom:-1px; }
.tab.active { color:var(--accent); border-bottom-color:var(--accent); }
.tab:hover { color:var(--ink); }
/* Badge ámbar para mesa Reservada (Task 4 lo usa) */
.badge--reservada { background:var(--accent-soft); color:#8a5a12; }
```

- [ ] **Step 7: Verificar que pasan**

Run: `docker compose exec web pytest tests/test_catalogo.py -v`
Expected: PASS los 9.

- [ ] **Step 8: Suite completa del web (no romper nada)**

Run: `docker compose exec web pytest`
Expected: PASS todo (86 previos + 5 de Task 1 + 9 nuevos).

- [ ] **Step 9: Commit**

```bash
git add web/app/catalogo/ web/app/templates/catalogo/ web/app/__init__.py web/app/templates/base.html web/app/static/css/app.css web/tests/test_catalogo.py
git commit -m "feat(web): módulo Catálogo con CRUD de productos (lista, filtros, form, toggle)"
```

---

### Task 3: Sub-recurso Categorías

**Files:**
- Modify: `web/app/catalogo/routes.py` (append), `web/app/templates/catalogo/_tabs.html`
- Create: `web/app/templates/catalogo/categorias_list.html`, `web/app/templates/catalogo/categorias_form.html`
- Test: `web/tests/test_catalogo.py` (append)

**Interfaces:**
- Consumes: de Task 1 — `list_categorias`, `get_categoria`, `create_categoria`, `update_categoria`, `delete_categoria`; de Task 2 — blueprint `bp`, stubs `_login`/`CATEGORIAS` en el test.
- Produces: endpoints `catalogo.categorias`, `catalogo.categoria_nueva`, `catalogo.categoria_crear`, `catalogo.categoria_editar`, `catalogo.categoria_actualizar`, `catalogo.categoria_eliminar`.

- [ ] **Step 1: Escribir los tests que fallan** — append a `web/tests/test_catalogo.py`:

```python
def test_lista_categorias_renderiza(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    cuerpo = client.get("/catalogo/categorias").get_data(as_text=True)
    assert "Bebidas calientes" in cuerpo
    assert "Postres" in cuerpo


def test_crear_categoria_ok_redirige(client, monkeypatch):
    _login(client, monkeypatch)
    capturado = {}

    def fake_create(access, payload):
        capturado["payload"] = payload
        return {"id_categoria": 9, **payload}

    monkeypatch.setattr(api_client, "create_categoria", fake_create)
    r = client.post("/catalogo/categorias", data={
        "nombre_categoria": "Ensaladas", "descripcion": "",
    })
    assert r.status_code == 302
    assert capturado["payload"] == {"nombre_categoria": "Ensaladas", "descripcion": None}


def test_crear_categoria_error_api_rerenderiza(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_create(access, payload):
        raise ApiError(409, "La categoría ya existe")

    monkeypatch.setattr(api_client, "create_categoria", fake_create)
    r = client.post("/catalogo/categorias", data={
        "nombre_categoria": "Postres", "descripcion": "",
    })
    assert r.status_code == 409
    assert "ya existe" in r.get_data(as_text=True)


def test_actualizar_categoria_llama_api(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_update(access, id_categoria, payload):
        llamado["id"] = id_categoria
        llamado["payload"] = payload
        return {"id_categoria": id_categoria, **payload}

    monkeypatch.setattr(api_client, "update_categoria", fake_update)
    r = client.post("/catalogo/categorias/2", data={
        "nombre_categoria": "Repostería", "descripcion": "Dulces",
    })
    assert r.status_code == 302
    assert llamado["id"] == 2
    assert llamado["payload"]["nombre_categoria"] == "Repostería"


def test_eliminar_categoria_ok(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}
    monkeypatch.setattr(
        api_client, "delete_categoria",
        lambda a, i: llamado.setdefault("id", i),
    )
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    r = client.post("/catalogo/categorias/2/eliminar", follow_redirects=True)
    assert r.status_code == 200
    assert llamado["id"] == 2
    assert "Categoría eliminada." in r.get_data(as_text=True)


def test_eliminar_categoria_con_productos_flashea_error(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_delete(access, id_categoria):
        raise ApiError(409, "La categoría tiene productos asociados")

    monkeypatch.setattr(api_client, "delete_categoria", fake_delete)
    monkeypatch.setattr(api_client, "list_categorias", lambda a: CATEGORIAS)
    r = client.post("/catalogo/categorias/1/eliminar", follow_redirects=True)
    assert r.status_code == 200  # la lista sigue viva
    assert "productos asociados" in r.get_data(as_text=True)
```

- [ ] **Step 2: Verificar que fallan**

Run: `docker compose exec web pytest tests/test_catalogo.py -v`
Expected: FAIL los 6 nuevos con 404; los de Task 2 PASS.

- [ ] **Step 3: Implementar rutas** — append a `web/app/catalogo/routes.py`:

```python
def _payload_categoria(form):
    return {
        "nombre_categoria": form["nombre_categoria"].strip(),
        "descripcion": (form.get("descripcion") or "").strip() or None,
    }


@bp.route("/categorias")
@login_required
def categorias():
    items = api_gateway.call(api_client.list_categorias)
    return render_template("catalogo/categorias_list.html", categorias=items)


@bp.route("/categorias/nueva")
@login_required
def categoria_nueva():
    return render_template("catalogo/categorias_form.html", categoria=None, form={})


@bp.route("/categorias", methods=["POST"])
@login_required
def categoria_crear():
    try:
        api_gateway.call(api_client.create_categoria, _payload_categoria(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        return (
            render_template("catalogo/categorias_form.html", categoria=None, form=request.form),
            e.status_code,
        )
    flash("Categoría creada.", "info")
    return redirect(url_for("catalogo.categorias"))


@bp.route("/categorias/<int:id_categoria>/editar")
@login_required
def categoria_editar(id_categoria):
    categoria = api_gateway.call(api_client.get_categoria, id_categoria)
    return render_template("catalogo/categorias_form.html", categoria=categoria, form=categoria)


@bp.route("/categorias/<int:id_categoria>", methods=["POST"])
@login_required
def categoria_actualizar(id_categoria):
    try:
        api_gateway.call(api_client.update_categoria, id_categoria, _payload_categoria(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        categoria = api_gateway.call(api_client.get_categoria, id_categoria)
        return (
            render_template("catalogo/categorias_form.html", categoria=categoria, form=request.form),
            e.status_code,
        )
    flash("Categoría actualizada.", "info")
    return redirect(url_for("catalogo.categorias"))


@bp.route("/categorias/<int:id_categoria>/eliminar", methods=["POST"])
@login_required
def categoria_eliminar(id_categoria):
    try:
        api_gateway.call(api_client.delete_categoria, id_categoria)
        flash("Categoría eliminada.", "info")
    except ApiError as e:
        flash(e.detail, "error")
    return redirect(url_for("catalogo.categorias"))
```

- [ ] **Step 4: Templates** — en `_tabs.html`, después del link de Productos, añadir:

```html
  <a class="tab {{ 'active' if tab == 'categorias' }}" href="{{ url_for('catalogo.categorias') }}">Categorías</a>
```

Crear `web/app/templates/catalogo/categorias_list.html`:

```html
{% extends "base.html" %}
{% block title %}Catálogo · Categorías — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>Catálogo</h1>
    <p class="sub">{{ categorias|length }} categoría(s)</p>
  </div>
  <a class="btn btn--accent" href="{{ url_for('catalogo.categoria_nueva') }}">+ Nueva categoría</a>
</div>

{% set tab = 'categorias' %}
{% include "catalogo/_tabs.html" %}

<div class="card" style="padding:0;overflow:hidden;">
<table class="table">
  <thead>
    <tr><th>Categoría</th><th>Descripción</th><th></th></tr>
  </thead>
  <tbody>
  {% for c in categorias %}
    <tr>
      <td>{{ c.nombre_categoria }}</td>
      <td>{{ c.descripcion or '—' }}</td>
      <td class="actions">
        <a class="icon-btn" href="{{ url_for('catalogo.categoria_editar', id_categoria=c.id_categoria) }}" title="Editar">✎</a>
        <form method="post" action="{{ url_for('catalogo.categoria_eliminar', id_categoria=c.id_categoria) }}"
              onsubmit="return confirm('¿Eliminar la categoría {{ c.nombre_categoria }}?')">
          <button class="link-danger" type="submit" title="Eliminar">Eliminar</button>
        </form>
      </td>
    </tr>
  {% else %}
    <tr><td colspan="3" class="muted">Sin categorías.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
```

Crear `web/app/templates/catalogo/categorias_form.html`:

```html
{% extends "base.html" %}
{% block title %}{{ 'Editar' if categoria else 'Nueva' }} categoría — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>{{ 'Editar' if categoria else 'Nueva' }} categoría</h1>
    <p class="sub">Agrupa los productos del menú</p>
  </div>
</div>

<form method="post"
      action="{{ url_for('catalogo.categoria_actualizar', id_categoria=categoria.id_categoria) if categoria else url_for('catalogo.categoria_crear') }}">
  <div class="card">
    <h2 class="card__title">Datos de la categoría</h2>
    <label>Nombre
      <input name="nombre_categoria" value="{{ form.get('nombre_categoria', '') }}" required></label>
    <label>Descripción
      <input name="descripcion" value="{{ form.get('descripcion', '') or '' }}"></label>
    <div class="header-row" style="margin-top:1rem;">
      <button type="submit">Guardar categoría</button>
      <a class="btn btn--ghost" href="{{ url_for('catalogo.categorias') }}">Cancelar</a>
    </div>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 5: Verificar que pasan**

Run: `docker compose exec web pytest tests/test_catalogo.py -v`
Expected: PASS los 15.

- [ ] **Step 6: Commit**

```bash
git add web/app/catalogo/routes.py web/app/templates/catalogo/ web/tests/test_catalogo.py
git commit -m "feat(web): CRUD de categorías en Catálogo (con eliminar FK-safe)"
```

---

### Task 4: Sub-recurso Mesas (regla de Ocupada)

**Files:**
- Modify: `web/app/catalogo/routes.py` (append), `web/app/templates/catalogo/_tabs.html`
- Create: `web/app/templates/catalogo/mesas_list.html`, `web/app/templates/catalogo/mesas_form.html`
- Test: `web/tests/test_catalogo.py` (append)

**Interfaces:**
- Consumes: de Task 1 — `list_mesas`, `get_mesa`, `create_mesa`, `update_mesa`, `delete_mesa`; de Task 2 — blueprint, `_login`, clase CSS `.badge--reservada`.
- Produces: endpoints `catalogo.mesas`, `catalogo.mesa_nueva`, `catalogo.mesa_crear`, `catalogo.mesa_editar`, `catalogo.mesa_actualizar`, `catalogo.mesa_eliminar`.

**Regla de negocio:** el form solo ofrece estado `Disponible`/`Reservada`. Si la mesa está `Ocupada`, el template no renderiza el `<select name="estado">` (muestra badge solo-lectura) y `_payload_mesa` solo incluye `estado` si viene en el form — así nunca se pisa una mesa ocupada.

- [ ] **Step 1: Escribir los tests que fallan** — append a `web/tests/test_catalogo.py`:

```python
MESAS = [
    {"id_mesa": 1, "numero_mesa": 1, "capacidad": 4, "ubicacion": "Terraza", "estado": "Disponible"},
    {"id_mesa": 2, "numero_mesa": 2, "capacidad": 2, "ubicacion": None, "estado": "Ocupada"},
    {"id_mesa": 3, "numero_mesa": 3, "capacidad": 6, "ubicacion": "Salón", "estado": "Reservada"},
]


def test_lista_mesas_renderiza_estados(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_mesas", lambda a: MESAS)
    cuerpo = client.get("/catalogo/mesas").get_data(as_text=True)
    assert "Terraza" in cuerpo
    assert "Disponible" in cuerpo
    assert "Ocupada" in cuerpo
    assert "Reservada" in cuerpo


def test_crear_mesa_ok_manda_payload_tipado(client, monkeypatch):
    _login(client, monkeypatch)
    capturado = {}

    def fake_create(access, payload):
        capturado["payload"] = payload
        return {"id_mesa": 9, **payload}

    monkeypatch.setattr(api_client, "create_mesa", fake_create)
    r = client.post("/catalogo/mesas", data={
        "numero_mesa": "11", "capacidad": "4", "ubicacion": "", "estado": "Disponible",
    })
    assert r.status_code == 302
    assert capturado["payload"] == {
        "numero_mesa": 11, "capacidad": 4, "ubicacion": None, "estado": "Disponible",
    }


def test_form_mesa_ocupada_no_ofrece_estado(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "get_mesa", lambda a, i: MESAS[1])
    cuerpo = client.get("/catalogo/mesas/2/editar").get_data(as_text=True)
    assert 'name="estado"' not in cuerpo  # sin selector
    assert "Ocupada" in cuerpo  # badge solo-lectura


def test_actualizar_mesa_sin_estado_no_lo_manda(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}

    def fake_update(access, id_mesa, payload):
        llamado["id"] = id_mesa
        llamado["payload"] = payload
        return {"id_mesa": id_mesa, **payload}

    monkeypatch.setattr(api_client, "update_mesa", fake_update)
    # el form de una mesa Ocupada postea sin campo estado
    r = client.post("/catalogo/mesas/2", data={
        "numero_mesa": "2", "capacidad": "4", "ubicacion": "Barra",
    })
    assert r.status_code == 302
    assert llamado["id"] == 2
    assert "estado" not in llamado["payload"]
    assert llamado["payload"]["capacidad"] == 4


def test_eliminar_mesa_referenciada_flashea_error(client, monkeypatch):
    _login(client, monkeypatch)
    from app.services.api_client import ApiError

    def fake_delete(access, id_mesa):
        raise ApiError(409, "La mesa tiene pedidos asociados")

    monkeypatch.setattr(api_client, "delete_mesa", fake_delete)
    monkeypatch.setattr(api_client, "list_mesas", lambda a: MESAS)
    r = client.post("/catalogo/mesas/1/eliminar", follow_redirects=True)
    assert r.status_code == 200
    assert "pedidos asociados" in r.get_data(as_text=True)


def test_eliminar_mesa_ok(client, monkeypatch):
    _login(client, monkeypatch)
    llamado = {}
    monkeypatch.setattr(api_client, "delete_mesa", lambda a, i: llamado.setdefault("id", i))
    monkeypatch.setattr(api_client, "list_mesas", lambda a: MESAS)
    r = client.post("/catalogo/mesas/1/eliminar", follow_redirects=True)
    assert r.status_code == 200
    assert llamado["id"] == 1
    assert "Mesa eliminada." in r.get_data(as_text=True)
```

- [ ] **Step 2: Verificar que fallan**

Run: `docker compose exec web pytest tests/test_catalogo.py -v`
Expected: FAIL los 6 nuevos con 404; el resto PASS.

- [ ] **Step 3: Implementar rutas** — append a `web/app/catalogo/routes.py`:

```python
def _payload_mesa(form):
    data = {
        "numero_mesa": int(form["numero_mesa"]),
        "capacidad": int(form["capacidad"]),
        "ubicacion": (form.get("ubicacion") or "").strip() or None,
    }
    # El form de una mesa Ocupada no manda estado: nunca se pisa desde el panel.
    if form.get("estado"):
        data["estado"] = form["estado"]
    return data


@bp.route("/mesas")
@login_required
def mesas():
    items = api_gateway.call(api_client.list_mesas)
    return render_template("catalogo/mesas_list.html", mesas=items)


@bp.route("/mesas/nueva")
@login_required
def mesa_nueva():
    return render_template("catalogo/mesas_form.html", mesa=None, form={})


@bp.route("/mesas", methods=["POST"])
@login_required
def mesa_crear():
    try:
        api_gateway.call(api_client.create_mesa, _payload_mesa(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        return (
            render_template("catalogo/mesas_form.html", mesa=None, form=request.form),
            e.status_code,
        )
    flash("Mesa creada.", "info")
    return redirect(url_for("catalogo.mesas"))


@bp.route("/mesas/<int:id_mesa>/editar")
@login_required
def mesa_editar(id_mesa):
    mesa = api_gateway.call(api_client.get_mesa, id_mesa)
    return render_template("catalogo/mesas_form.html", mesa=mesa, form=mesa)


@bp.route("/mesas/<int:id_mesa>", methods=["POST"])
@login_required
def mesa_actualizar(id_mesa):
    try:
        api_gateway.call(api_client.update_mesa, id_mesa, _payload_mesa(request.form))
    except ApiError as e:
        flash(e.detail, "error")
        mesa = api_gateway.call(api_client.get_mesa, id_mesa)
        return (
            render_template("catalogo/mesas_form.html", mesa=mesa, form=request.form),
            e.status_code,
        )
    flash("Mesa actualizada.", "info")
    return redirect(url_for("catalogo.mesas"))


@bp.route("/mesas/<int:id_mesa>/eliminar", methods=["POST"])
@login_required
def mesa_eliminar(id_mesa):
    try:
        api_gateway.call(api_client.delete_mesa, id_mesa)
        flash("Mesa eliminada.", "info")
    except ApiError as e:
        flash(e.detail, "error")
    return redirect(url_for("catalogo.mesas"))
```

- [ ] **Step 4: Templates** — en `_tabs.html`, después del link de Categorías, añadir:

```html
  <a class="tab {{ 'active' if tab == 'mesas' }}" href="{{ url_for('catalogo.mesas') }}">Mesas</a>
```

Crear `web/app/templates/catalogo/mesas_list.html`:

```html
{% extends "base.html" %}
{% block title %}Catálogo · Mesas — Cafetería Aroma{% endblock %}
{% set badge_de = {'Disponible': 'on', 'Ocupada': 'off', 'Reservada': 'reservada'} %}
{% block content %}
<div class="page-head">
  <div>
    <h1>Catálogo</h1>
    <p class="sub">{{ mesas|length }} mesa(s)</p>
  </div>
  <a class="btn btn--accent" href="{{ url_for('catalogo.mesa_nueva') }}">+ Nueva mesa</a>
</div>

{% set tab = 'mesas' %}
{% include "catalogo/_tabs.html" %}

<div class="card" style="padding:0;overflow:hidden;">
<table class="table">
  <thead>
    <tr><th>Mesa</th><th>Capacidad</th><th>Ubicación</th><th>Estado</th><th></th></tr>
  </thead>
  <tbody>
  {% for m in mesas %}
    <tr>
      <td>Mesa {{ m.numero_mesa }}</td>
      <td>{{ m.capacidad }} persona(s)</td>
      <td>{{ m.ubicacion or '—' }}</td>
      <td><span class="badge badge--{{ badge_de.get(m.estado, 'off') }}">{{ m.estado }}</span></td>
      <td class="actions">
        <a class="icon-btn" href="{{ url_for('catalogo.mesa_editar', id_mesa=m.id_mesa) }}" title="Editar">✎</a>
        <form method="post" action="{{ url_for('catalogo.mesa_eliminar', id_mesa=m.id_mesa) }}"
              onsubmit="return confirm('¿Eliminar la mesa {{ m.numero_mesa }}?')">
          <button class="link-danger" type="submit" title="Eliminar">Eliminar</button>
        </form>
      </td>
    </tr>
  {% else %}
    <tr><td colspan="5" class="muted">Sin mesas.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
```

Crear `web/app/templates/catalogo/mesas_form.html`:

```html
{% extends "base.html" %}
{% block title %}{{ 'Editar' if mesa else 'Nueva' }} mesa — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>{{ 'Editar' if mesa else 'Nueva' }} mesa</h1>
    <p class="sub">Define la mesa y su capacidad</p>
  </div>
</div>

<form method="post"
      action="{{ url_for('catalogo.mesa_actualizar', id_mesa=mesa.id_mesa) if mesa else url_for('catalogo.mesa_crear') }}">
  <div class="card">
    <h2 class="card__title">Datos de la mesa</h2>
    <label>Número de mesa
      <input type="number" name="numero_mesa" value="{{ form.get('numero_mesa', '') }}" min="1" required></label>
    <label>Capacidad (personas)
      <input type="number" name="capacidad" value="{{ form.get('capacidad', '') }}" min="1" required></label>
    <label>Ubicación
      <input name="ubicacion" value="{{ form.get('ubicacion', '') or '' }}"></label>
    {% if mesa and mesa.estado == 'Ocupada' %}
    <label>Estado</label>
    <p><span class="badge badge--off">Ocupada</span><br>
      <small>La ocupación la controla el flujo de pedidos; la mesa se libera al cobrar.</small></p>
    {% else %}
    <label>Estado
      <select name="estado">
        <option value="Disponible" {{ 'selected' if form.get('estado', 'Disponible') == 'Disponible' }}>Disponible</option>
        <option value="Reservada" {{ 'selected' if form.get('estado') == 'Reservada' }}>Reservada</option>
      </select></label>
    {% endif %}
    <div class="header-row" style="margin-top:1rem;">
      <button type="submit">Guardar mesa</button>
      <a class="btn btn--ghost" href="{{ url_for('catalogo.mesas') }}">Cancelar</a>
    </div>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 5: Verificar que pasan**

Run: `docker compose exec web pytest tests/test_catalogo.py -v`
Expected: PASS los 21.

- [ ] **Step 6: Commit**

```bash
git add web/app/catalogo/routes.py web/app/templates/catalogo/ web/tests/test_catalogo.py
git commit -m "feat(web): CRUD de mesas en Catálogo (estado protegido cuando Ocupada)"
```

---

### Task 5: Verificación integral y documentación

**Files:**
- Modify: `progress.md`

**Interfaces:**
- Consumes: todo lo anterior mergeado en la rama de trabajo.
- Produces: suite completa verde + verificación visual en la app real + `progress.md` actualizado.

- [ ] **Step 1: Suite completa del web**

Run: `docker compose exec web pytest`
Expected: PASS todo — 86 previos + 5 (Task 1) + 21 (`test_catalogo.py`) = 112.

- [ ] **Step 2: Verificación visual en la app real**

```bash
docker compose up -d
docker compose restart web   # el hot-reload no recarga el registro del blueprint
```

Abrir `http://localhost:5000` (login `admin@cafeteria.com`) y verificar la checklist:
- El sidebar muestra "Catálogo" entre Usuarios y Reportes y queda activo al entrar.
- `/catalogo` cae en Productos; las 3 pestañas navegan y marcan la activa.
- Productos: precios se ven `$ 45.00` (string tal cual), filtros de categoría/estado recargan filtrado, toggle Activar/Desactivar cambia el badge, crear/editar funcionan y un precio negativo muestra el error de la API como flash sin perder lo tecleado.
- Categorías: crear/editar; eliminar una categoría con productos muestra el error FK como flash (la lista sobrevive).
- Mesas: badges por estado (verde/rojo/ámbar); editar una mesa Ocupada no ofrece selector de estado; alternar Disponible ⇄ Reservada sí funciona; eliminar una mesa con pedidos muestra el error FK.

- [ ] **Step 3: Actualizar `progress.md`**

En la sección Sprint 6 (o nueva subsección "Post-Sprint 6"), documentar el módulo Catálogo (blueprint, 3 sub-recursos, semántica de borrado, regla de Ocupada, conteo de tests). Quitar la línea "CRUD de catálogo en la **web admin** (hoy solo vía API/Swagger)" de *Deuda técnica* y actualizar el conteo de tests web (86 → 112).

- [ ] **Step 4: Commit**

```bash
git add progress.md
git commit -m "docs: progress.md — módulo Catálogo web (productos/categorías/mesas)"
```

---

## Self-review del plan (hecho al escribirlo)

- **Cobertura del spec:** navegación con tabs (T2–T4), 14 funciones api_client (T1), toggle de productos (T2), eliminar FK-safe con flash (T3/T4), regla de mesa Ocupada (T4), Decimal-string en templates y stubs (T2), sidebar (T2), restart del contenedor (T5), fuera-de-alcance respetado (no se toca backend).
- **Sin placeholders:** cada step tiene el código/comando/resultado esperado completo.
- **Consistencia de tipos:** firmas de `api_client` idénticas entre T1 (Produces) y T2–T4 (Consumes); nombres de endpoint `catalogo.*` consistentes entre routes, templates y tests; `_tabs.html` crece incrementalmente (T2 productos → T3 categorías → T4 mesas) para que `url_for` nunca apunte a un endpoint inexistente.
