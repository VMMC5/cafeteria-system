# Rediseño del panel web ("Cafetería Aroma") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rediseñar el panel web admin (Flask) con la identidad "Cafetería Aroma" (tema café + sidebar), re-estilizando login, Estadísticas (dashboard del Slice A) y Usuarios (lista/form), sin cambios de backend.

**Architecture:** Solo presentación: un `app.css` con sistema de diseño (tokens + componentes), un shell autenticado con sidebar (`base.html`), un layout público para el login (`base_public.html`), y rewrites de markup por página. La única lógica nueva es el filtrado de la lista de usuarios por Rol/Estado en la ruta Flask (sobre datos ya devueltos por la API). Se preserva el patrón cliente delgado.

**Tech Stack:** Flask + Jinja2 + CSS (sin dependencias externas), pytest (web).

## Global Constraints

- **Sin cambios de backend/API, sin migraciones.** Solo `web/`.
- **Marca:** login = "Cafetería **Aroma**" + "Panel de Administración General"; sidebar = "☕ Café **Admin**".
- **Tokens de color (en `:root`):** `--bg:#f0ebe4`, `--surface:#ffffff`, `--sidebar:#3a2a20`, `--sidebar-2:#2c1e16`, `--ink:#2c1e16`, `--ink-soft:#6b5647`, `--muted:#9a8577`, `--accent:#c8862f`, `--accent-soft:#f6e6c9`, `--border:#e7ddd3`, `--gain:#2f7d4f`, `--loss:#c0483b`.
- **Tipografía (stacks del sistema, sin web fonts):** serif `Georgia, 'Times New Roman', serif` (títulos/marca); cuerpo `system-ui, -apple-system, sans-serif`; mono `ui-monospace, 'SFMono-Regular', Menlo, monospace` (números/tablas).
- **Badges de rol:** Administrador=`badge--admin` (morado), Cajero=`badge--cajero` (café), Cocinero=`badge--cocinero` (verde), Mesero=`badge--mesero` (ámbar).
- **Campos reales de usuario** (NO agregar teléfono): `nombre`, `apellido_paterno`, `apellido_materno`, `correo`, `nombre_usuario`, `password`.
- **No romper aserciones de tests existentes** — deben seguir presentes: `"Iniciar"` (login), `"$400.00"` y `"Utilidad"` (estadísticas), `id="chart-ventas"`/`id="chart-top"`/`"chart.umd.min.js"`/`"Café"` (gráficas), redirect a `"/usuarios"` tras login admin, flashes con `"incorrect"` (401) y `"administrador"` (403), y `"Ana"`/`"Mesero"` en la lista.
- **Tests web:** `docker compose exec web pytest` (contenedor `web` arriba, código montado).
- **Verificación manual:** tras cambios de plantilla/registro hay que **reiniciar** el contenedor `web` (`docker compose restart web`) — el hot-reload no recarga plantillas base ni rutas nuevas.

---

## File Structure

**Web (crear):**
- `web/app/templates/base_public.html` — layout mínimo (sin sidebar) para el login.

**Web (modificar):**
- `web/app/static/css/app.css` — reescritura completa: sistema de diseño (tokens + componentes de todas las páginas). Mantiene también las clases que usan las plantillas aún no re-maquetadas, para que nada se rompa entre tareas.
- `web/app/templates/base.html` — shell autenticado con sidebar.
- `web/app/templates/auth/login.html` — pasa a `base_public`; split brand/card (Task 2).
- `web/app/templates/dashboard/index.html` — restyle "Estadísticas" (Task 3).
- `web/app/dashboard/routes.py` — sin cambios funcionales (solo si hiciera falta pasar contexto; no requerido).
- `web/app/usuarios/routes.py` — filtros Rol/Estado en `listar` (Task 4).
- `web/app/templates/usuarios/list.html` — rediseño lista (Task 4).
- `web/app/templates/usuarios/form.html` — rediseño form (Task 5).
- `web/tests/test_web_ui.py` (crear) — tests del shell/redesign.

---

## Task 1: Sistema de diseño + shell con sidebar + layout público

**Files:**
- Modify: `web/app/static/css/app.css`
- Modify: `web/app/templates/base.html`
- Create: `web/app/templates/base_public.html`
- Modify: `web/app/templates/auth/login.html`
- Test: `web/tests/test_web_ui.py`

**Interfaces:**
- Produces: shell autenticado (`base.html`) con sidebar de marca "Café Admin" y enlaces `dashboard.index` (Estadísticas) + `usuarios.listar` (Usuarios y Roles), footer de usuario con avatar de iniciales; `base_public.html` con bloque `{% block fullpage %}`. El login pasa a extender `base_public`.

- [ ] **Step 1: Write the failing test**

Crear `web/tests/test_web_ui.py`:

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


def _login(client, monkeypatch):
    monkeypatch.setattr(api_client, "login", lambda c, p: ADMIN_TOKENS)
    monkeypatch.setattr(api_client, "get_me", lambda a: ADMIN_ME)
    client.post("/login", data={"correo": "admin@cafeteria.com", "password": "x"})


def test_shell_tiene_sidebar_con_marca_y_enlaces(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: [])
    cuerpo = client.get("/usuarios").get_data(as_text=True)
    assert "sidebar" in cuerpo
    assert "Café" in cuerpo and "Admin" in cuerpo      # marca
    assert "Estadísticas" in cuerpo                     # enlace nav
    assert "Usuarios y Roles" in cuerpo                 # enlace nav


def test_login_usa_layout_publico_sin_sidebar(client):
    cuerpo = client.get("/login").get_data(as_text=True)
    assert "Iniciar" in cuerpo
    assert 'class="sidebar"' not in cuerpo              # el login no muestra sidebar
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_web_ui.py -v`
Expected: FAIL — el markup actual no tiene `class="sidebar"` ni "Estadísticas".

- [ ] **Step 3: Reescribir `web/app/static/css/app.css`**

Reemplazar TODO el contenido de `web/app/static/css/app.css` por:

```css
:root {
  --bg:#f0ebe4; --surface:#ffffff; --sidebar:#3a2a20; --sidebar-2:#2c1e16;
  --ink:#2c1e16; --ink-soft:#6b5647; --muted:#9a8577; --accent:#c8862f;
  --accent-soft:#f6e6c9; --border:#e7ddd3; --gain:#2f7d4f; --loss:#c0483b;
  --serif:Georgia,'Times New Roman',serif;
  --mono:ui-monospace,'SFMono-Regular',Menlo,monospace;
  --shadow:0 1px 3px rgba(60,40,25,.12); --radius:12px;
}
* { box-sizing:border-box; }
body { margin:0; font-family:system-ui,-apple-system,sans-serif; color:var(--ink); background:var(--bg); }
a { color:var(--accent); }
h1,h2,h3 { font-family:var(--serif); }

/* App shell */
.app { display:flex; min-height:100vh; }
.sidebar { width:230px; background:var(--sidebar); color:#e9ddd2; display:flex; flex-direction:column; flex-shrink:0; }
.sidebar__brand { font-family:var(--serif); font-size:1.25rem; padding:1.1rem 1.25rem; color:#fff; }
.sidebar__brand b { color:var(--accent); }
.sidebar__nav { display:flex; flex-direction:column; padding:.5rem; gap:.15rem; flex:1; }
.sidebar__link { display:flex; align-items:center; gap:.6rem; padding:.6rem .75rem; border-radius:8px; color:#d9c9bb; text-decoration:none; font-size:.95rem; }
.sidebar__link:hover { background:rgba(255,255,255,.06); color:#fff; }
.sidebar__link.active { background:var(--accent-soft); color:var(--sidebar-2); font-weight:600; }
.sidebar__link svg { width:18px; height:18px; }
.sidebar__user { display:flex; align-items:center; gap:.6rem; padding:1rem 1.25rem; border-top:1px solid rgba(255,255,255,.08); font-size:.9rem; }
.sidebar__user small { color:var(--accent); }
.avatar { width:34px; height:34px; border-radius:50%; background:var(--accent); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.85rem; flex-shrink:0; }

.main { flex:1; min-width:0; }
.content { max-width:1080px; margin:0 auto; padding:1.5rem; }
.page-head { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:1.25rem; gap:1rem; }
.page-head h1 { margin:0; font-size:1.9rem; }
.page-head .sub { color:var(--ink-soft); margin:.15rem 0 0; }

/* Cards */
.card { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:1.25rem; box-shadow:var(--shadow); }
.card__title { font-family:var(--serif); margin:0 0 .9rem; font-size:1.1rem; }

/* Buttons */
button,.btn { background:var(--sidebar); color:#fff; border:0; padding:.55rem 1rem; border-radius:8px; font-size:.95rem; cursor:pointer; text-decoration:none; display:inline-block; font-family:inherit; }
button:hover,.btn:hover { background:var(--sidebar-2); }
.btn--accent { background:var(--accent); } .btn--accent:hover { background:#a96f1f; }
.btn--ghost { background:transparent; color:var(--ink); border:1px solid var(--border); }
.btn--ghost:hover { background:var(--bg); }

/* Forms */
label { display:block; margin:.7rem 0; font-weight:600; font-size:.9rem; }
input,select { width:100%; padding:.55rem .65rem; margin-top:.25rem; border:1px solid var(--border); border-radius:8px; font-size:.95rem; font-family:inherit; background:#fbf8f4; color:var(--ink); }
input:focus,select:focus { outline:2px solid var(--accent-soft); border-color:var(--accent); }
small { display:block; font-weight:400; margin-top:.25rem; color:var(--muted); }
.inline { display:flex; align-items:center; gap:.5rem; font-weight:400; }
.inline input { width:auto; margin:0; }

/* Flash */
.flash { padding:.65rem 1rem; border-radius:8px; margin-bottom:1rem; }
.flash--error { background:#f7dcd8; color:#7a2c22; }
.flash--info { background:var(--accent-soft); color:#6b4423; }
.muted { color:var(--muted); }

/* Tables */
.table { width:100%; border-collapse:collapse; background:var(--surface); }
.table th,.table td { padding:.75rem .85rem; border-bottom:1px solid var(--border); text-align:left; }
.table th { font-size:.72rem; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); font-weight:600; }
.table tr:last-child td { border-bottom:0; }

/* Badges */
.badge { padding:.2rem .6rem; border-radius:999px; font-size:.72rem; font-weight:600; letter-spacing:.03em; text-transform:uppercase; }
.badge--admin { background:#ede9fe; color:#5b21b6; }
.badge--cajero { background:#efe6da; color:#6b4423; }
.badge--cocinero { background:#d8efdd; color:#1f6b3a; }
.badge--mesero { background:#f6e6c9; color:#8a5a12; }
.dot { display:inline-block; width:8px; height:8px; border-radius:50%; margin-right:.4rem; }
.dot--on { background:var(--gain); } .dot--off { background:var(--muted); }
.state--on { color:var(--gain); } .state--off { color:var(--muted); }

/* Users list */
.userline { display:flex; align-items:center; gap:.7rem; }
.userline small { color:var(--muted); margin:0; }
.toolbar { display:flex; gap:.6rem; margin-bottom:1rem; flex-wrap:wrap; }
.search { display:flex; gap:.5rem; flex:1; }
.search input { flex:1; margin:0; }
.actions { display:flex; gap:.5rem; align-items:center; }
.actions form { margin:0; }
.icon-btn { background:var(--bg); border:1px solid var(--border); color:var(--ink-soft); width:32px; height:32px; border-radius:8px; padding:0; display:inline-flex; align-items:center; justify-content:center; }
.icon-btn:hover { background:var(--accent-soft); }
.link-danger { background:none; color:var(--loss); padding:0; border:0; cursor:pointer; }
.link-danger:hover { text-decoration:underline; background:none; }

/* KPIs */
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:1rem; margin:1rem 0; }
.kpi { background:var(--surface); border:1px solid var(--border); border-top:3px solid var(--border); border-radius:var(--radius); padding:1rem 1.1rem; box-shadow:var(--shadow); }
.kpi--accent { border-top-color:var(--accent); }
.kpi__label { font-size:.72rem; letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }
.kpi__value { font-family:var(--mono); font-size:1.6rem; font-weight:700; margin-top:.3rem; }

/* Period pills */
.filtros { display:flex; gap:.5rem; align-items:center; margin-bottom:1rem; flex-wrap:wrap; }
.pill { border:1px solid var(--border); background:var(--surface); border-radius:999px; padding:.35rem .8rem; cursor:pointer; font-size:.85rem; color:var(--ink-soft); font-family:inherit; }
.pill.active { background:var(--accent); color:#fff; border-color:var(--accent); }

/* Charts */
.graficas { display:grid; grid-template-columns:repeat(auto-fit,minmax(320px,1fr)); gap:1.25rem; margin-top:1.25rem; }
.grafica { background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:1.1rem; box-shadow:var(--shadow); }
.grafica h2 { font-family:var(--serif); font-size:1.05rem; margin:0 0 .8rem; }

/* Two-column (user form) */
.cols { display:grid; grid-template-columns:1.4fr 1fr; gap:1.25rem; align-items:start; }
.stack { display:grid; gap:1.25rem; }
.role-cards { display:grid; gap:.5rem; }
.role-card { display:flex; align-items:center; gap:.6rem; border:1px solid var(--border); border-radius:10px; padding:.7rem .8rem; cursor:pointer; font-weight:600; }
.role-card input { width:auto; margin:0; }
.role-card.selected { border-color:var(--accent); box-shadow:0 0 0 1px var(--accent); }
.perms { list-style:none; padding:0; margin:0; display:grid; gap:.4rem; }
.perms li { display:flex; align-items:center; gap:.5rem; font-size:.9rem; color:var(--ink-soft); }
.perms li::before { content:"✓"; color:var(--gain); font-weight:700; }

/* Login (public) */
.login { min-height:100vh; display:grid; grid-template-columns:1fr 1fr; }
.login__brand { background:var(--sidebar-2); color:#fff; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:2rem; text-align:center; }
.login__brand h1 { font-family:var(--serif); font-size:2.4rem; margin:.5rem 0 0; }
.login__brand h1 b { color:var(--accent); }
.login__brand .sub { color:#c9b6a5; font-style:italic; }
.login__panel { display:flex; align-items:center; justify-content:center; padding:2rem; background:var(--bg); }
.login__card { background:var(--surface); border:1px solid var(--border); border-radius:16px; box-shadow:var(--shadow); padding:2rem; width:100%; max-width:380px; }
.login__card h1 { text-align:center; margin:0 0 .2rem; font-size:1.6rem; }
.login__card .sub { text-align:center; color:var(--accent); font-size:.85rem; margin:0 0 1.2rem; }
.login__card button { width:100%; margin-top:.6rem; }
.card--narrow { background:var(--surface); border:1px solid var(--border); border-radius:16px; box-shadow:var(--shadow); padding:2rem; max-width:380px; margin:3rem auto; }

/* Legacy compat (plantillas aún no re-maquetadas) */
.header-row { display:flex; justify-content:space-between; align-items:center; }
.badge--on { background:#d8efdd; color:#1f6b3a; }
.badge--off { background:#f7dcd8; color:#7a2c22; }

/* Responsive */
@media (max-width:768px) {
  .app { flex-direction:column; }
  .sidebar { width:100%; flex-direction:row; align-items:center; overflow-x:auto; }
  .sidebar__nav { flex-direction:row; flex:1; }
  .sidebar__user { border-top:0; }
  .cols { grid-template-columns:1fr; }
  .login { grid-template-columns:1fr; }
}
```

- [ ] **Step 4: Reescribir `web/app/templates/base.html`** (shell autenticado con sidebar)

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Cafetería Aroma · Admin{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="sidebar__brand">☕ Café <b>Admin</b></div>
    <nav class="sidebar__nav">
      <a class="sidebar__link {{ 'active' if request.endpoint == 'dashboard.index' }}" href="{{ url_for('dashboard.index') }}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 13h6V4H4zM14 20h6v-9h-6zM4 20h6v-4H4zM14 8h6V4h-6z"/></svg>
        Estadísticas
      </a>
      <a class="sidebar__link {{ 'active' if request.endpoint and request.endpoint.startswith('usuarios.') }}" href="{{ url_for('usuarios.listar') }}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="8" r="3"/><path d="M3 20c0-3 3-5 6-5s6 2 6 5"/><circle cx="17" cy="9" r="2"/></svg>
        Usuarios y Roles
      </a>
    </nav>
    <div class="sidebar__user">
      <span class="avatar">{{ (current_user.nombre[0] if current_user.nombre else 'U')|upper }}</span>
      <div>{{ current_user.nombre }}<br><small>Administrador</small></div>
    </div>
  </aside>
  <main class="main">
    <div class="content">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}
          <div class="flash flash--{{ category }}">{{ msg }}</div>
        {% endfor %}
      {% endwith %}
      {% block content %}{% endblock %}
    </div>
  </main>
</div>
</body>
</html>
```

- [ ] **Step 5: Crear `web/app/templates/base_public.html`**

```html
<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Cafetería Aroma{% endblock %}</title>
  <link rel="stylesheet" href="{{ url_for('static', filename='css/app.css') }}">
</head>
<body>
  {% block fullpage %}{% endblock %}
</body>
</html>
```

- [ ] **Step 6: Actualizar `web/app/templates/auth/login.html`** (interino: extiende `base_public`, sigue funcional; el split va en Task 2)

```html
{% extends "base_public.html" %}
{% block title %}Iniciar sesión{% endblock %}
{% block fullpage %}
<div class="card--narrow">
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% for category, msg in messages %}<div class="flash flash--{{ category }}">{{ msg }}</div>{% endfor %}
  {% endwith %}
  <h1>Iniciar sesión</h1>
  <form method="post" action="{{ url_for('auth.login') }}">
    <label>Correo <input type="email" name="correo" required autofocus></label>
    <label>Contraseña <input type="password" name="password" required></label>
    <button type="submit">Entrar</button>
  </form>
  <p class="muted"><a href="{{ support_url }}">¿Problemas para entrar? Contacta soporte</a></p>
</div>
{% endblock %}
```

- [ ] **Step 7: Run the new + existing tests**

Run: `docker compose exec web pytest tests/test_web_ui.py tests/test_auth.py -v`
Expected: PASS — el shell tiene sidebar/marca/enlaces; el login renderiza sin sidebar y conserva "Iniciar"; los flashes de auth (401 "incorrect", 403 "administrador") siguen mostrándose.

- [ ] **Step 8: Run the full web suite (no regresiones)**

Run: `docker compose exec web pytest`
Expected: PASS (los 21 previos + los nuevos). Las plantillas aún no re-maquetadas (dashboard/usuarios) siguen funcionando gracias a las clases legacy conservadas.

- [ ] **Step 9: Commit**

```bash
git add web/app/static/css/app.css web/app/templates/base.html \
        web/app/templates/base_public.html web/app/templates/auth/login.html \
        web/tests/test_web_ui.py
git commit -m "feat(web): sistema de diseño Cafetería Aroma + shell con sidebar"
```

---

## Task 2: Login split (marca + tarjeta)

**Files:**
- Modify: `web/app/templates/auth/login.html`
- Test: `web/tests/test_web_ui.py`

**Interfaces:**
- Consumes: `base_public.html` (bloque `fullpage`), `support_url` (lo pasa `auth.routes`).
- Produces: login de dos columnas (`.login` > `.login__brand` + `.login__panel` > `.login__card`).

- [ ] **Step 1: Write the failing test**

Añadir a `web/tests/test_web_ui.py`:

```python
def test_login_split_marca_y_subtitulo(client):
    cuerpo = client.get("/login").get_data(as_text=True)
    assert "login__brand" in cuerpo
    assert "Aroma" in cuerpo                                  # marca completa
    assert "Acceso exclusivo para administradores" in cuerpo  # subtítulo del card
    assert "Ingresar" in cuerpo                               # botón
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_web_ui.py::test_login_split_marca_y_subtitulo -v`
Expected: FAIL — el login interino no tiene `login__brand` ni el subtítulo.

- [ ] **Step 3: Reescribir `web/app/templates/auth/login.html`** (split)

```html
{% extends "base_public.html" %}
{% block title %}Iniciar sesión — Cafetería Aroma{% endblock %}
{% block fullpage %}
<div class="login">
  <div class="login__brand">
    <svg width="90" height="90" viewBox="0 0 24 24" fill="none" stroke="#c8862f" stroke-width="1.5">
      <path d="M4 8h13v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5V8z"/>
      <path d="M17 9h2a2 2 0 0 1 0 4h-2"/>
      <path d="M8 3c0 1-1 1.5-1 2.5M11 3c0 1-1 1.5-1 2.5M14 3c0 1-1 1.5-1 2.5" stroke-linecap="round"/>
    </svg>
    <h1>Cafetería <b>Aroma</b></h1>
    <p class="sub">Panel de Administración General</p>
  </div>
  <div class="login__panel">
    <div class="login__card">
      {% with messages = get_flashed_messages(with_categories=true) %}
        {% for category, msg in messages %}<div class="flash flash--{{ category }}">{{ msg }}</div>{% endfor %}
      {% endwith %}
      <h1>Iniciar sesión</h1>
      <p class="sub">Acceso exclusivo para administradores</p>
      <form method="post" action="{{ url_for('auth.login') }}">
        <label>Correo electrónico
          <input type="email" name="correo" placeholder="admin@cafeteria.com" required autofocus>
        </label>
        <label>Contraseña
          <input type="password" name="password" required>
        </label>
        <button type="submit">Ingresar</button>
      </form>
      <p class="muted" style="text-align:center;margin-top:1rem;">
        <a href="{{ support_url }}">¿Problemas para acceder? Contacta a soporte</a>
      </p>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `docker compose exec web pytest tests/test_web_ui.py tests/test_auth.py -v`
Expected: PASS — nuevo split presente; `test_get_login_ok` ("Iniciar") y los flashes de auth siguen verdes.

- [ ] **Step 5: Commit**

```bash
git add web/app/templates/auth/login.html web/tests/test_web_ui.py
git commit -m "feat(web): login split con marca Cafetería Aroma"
```

---

## Task 3: Estadísticas (restyle del dashboard)

**Files:**
- Modify: `web/app/templates/dashboard/index.html`
- Test: `web/tests/test_dashboard.py` (existentes; no cambian sus asserts)

**Interfaces:**
- Consumes: contexto ya provisto por `dashboard.routes.index` (`resumen`, `serie`, `top`, `preset`, `desde`, `hasta`). Sin cambios en la ruta.
- Produces: página "Estadísticas" con `page-head`, pills de periodo, KPIs y gráficas re-estilizadas. Mantiene `id="chart-ventas"`, `id="chart-top"`, el `<script src=...chart.umd.min.js>` y el formato `$%.2f` con la etiqueta "Utilidad estimada".

- [ ] **Step 1: Confirmar los asserts que deben seguir pasando**

Los tests de `web/tests/test_dashboard.py` exigen en el HTML: `"$400.00"`, `"Utilidad"`, `id="chart-ventas"`, `id="chart-top"`, `"chart.umd.min.js"`, `"Café"`. El rewrite debe conservarlos. (No se escriben tests nuevos en esta tarea.)

- [ ] **Step 2: Reescribir `web/app/templates/dashboard/index.html`**

```html
{% extends "base.html" %}
{% block title %}Estadísticas — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>Estadísticas</h1>
    <p class="sub">Panel de indicadores</p>
  </div>
</div>

<form method="get" class="filtros">
  <button type="submit" name="preset" value="hoy"   class="pill {{ 'active' if preset == 'hoy' }}">Hoy</button>
  <button type="submit" name="preset" value="7dias" class="pill {{ 'active' if preset == '7dias' }}">7 días</button>
  <button type="submit" name="preset" value="mes"   class="pill {{ 'active' if preset == 'mes' }}">Este mes</button>
  <input type="date" name="desde" value="{{ desde }}">
  <input type="date" name="hasta" value="{{ hasta }}">
  <button type="submit" name="preset" value="rango" class="pill {{ 'active' if preset == 'rango' }}">Aplicar rango</button>
</form>

<section class="kpis">
  <div class="kpi"><span class="kpi__label">Total vendido</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.total_vendido|float) }}</span></div>
  <div class="kpi"><span class="kpi__label"># Ventas</span>
    <span class="kpi__value">{{ resumen.num_ventas }}</span></div>
  <div class="kpi"><span class="kpi__label">Ticket promedio</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.ticket_promedio|float) }}</span></div>
  <div class="kpi"><span class="kpi__label">Gastos</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.total_gastos|float) }}</span></div>
  <div class="kpi"><span class="kpi__label">Compras</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.total_compras|float) }}</span></div>
  <div class="kpi kpi--accent"><span class="kpi__label">Utilidad estimada</span>
    <span class="kpi__value">${{ '%.2f'|format(resumen.utilidad_estimada|float) }}</span></div>
</section>

<section class="graficas">
  <div class="grafica"><h2>Ventas por día</h2><canvas id="chart-ventas"></canvas></div>
  <div class="grafica"><h2>Productos más vendidos</h2><canvas id="chart-top"></canvas></div>
</section>

<script id="serie-data" type="application/json">{{ serie|tojson }}</script>
<script id="top-data" type="application/json">{{ top|tojson }}</script>
<script src="{{ url_for('static', filename='vendor/chart.umd.min.js') }}"></script>
<script>
  const serie = JSON.parse(document.getElementById("serie-data").textContent);
  const top = JSON.parse(document.getElementById("top-data").textContent);
  new Chart(document.getElementById("chart-ventas"), {
    type: "line",
    data: {
      labels: serie.map(p => p.fecha),
      datasets: [{ label: "Ventas ($)", data: serie.map(p => Number(p.total)),
                   borderColor: "#c8862f", backgroundColor: "rgba(200,134,47,.15)",
                   fill: true, tension: 0.3 }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
  new Chart(document.getElementById("chart-top"), {
    type: "bar",
    data: {
      labels: top.map(p => p.nombre),
      datasets: [{ label: "Cantidad", data: top.map(p => Number(p.cantidad)),
                   backgroundColor: "#3a2a20" }],
    },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
</script>
{% endblock %}
```

- [ ] **Step 3: Run the dashboard tests**

Run: `docker compose exec web pytest tests/test_dashboard.py -v`
Expected: PASS (8 tests) — `$400.00`, `Utilidad`, ids de canvas, `chart.umd.min.js` y `Café` siguen presentes.

- [ ] **Step 4: Commit**

```bash
git add web/app/templates/dashboard/index.html
git commit -m "feat(web): restyle Estadísticas (KPIs + gráficas tema café)"
```

---

## Task 4: Usuarios y Roles (lista + filtros)

**Files:**
- Modify: `web/app/usuarios/routes.py`
- Modify: `web/app/templates/usuarios/list.html`
- Test: `web/tests/test_web_ui.py`

**Interfaces:**
- Consumes: `api_gateway.call(api_client.list_usuarios, q)` (ya existe).
- Produces: `usuarios.listar` acepta `?q&rol&estado` y filtra en Python la lista devuelta; la plantilla muestra avatar de iniciales, badge de rol (`badge--{admin,cajero,cocinero,mesero}`), punto de estado y acciones. Los `<select>` de Rol/Estado hacen GET.

- [ ] **Step 1: Write the failing test**

Añadir a `web/tests/test_web_ui.py`:

```python
def _users():
    return [
        {"id_usuario": 1, "nombre": "Eduardo", "apellido_paterno": "Gutiérrez",
         "correo": "eduardo@cafeteria.com", "activo": True,
         "rol": {"nombre_rol": "Mesero"}},
        {"id_usuario": 2, "nombre": "Rafael", "apellido_paterno": "Baltazar",
         "correo": "rafael@cafeteria.com", "activo": False,
         "rol": {"nombre_rol": "Cocinero"}},
    ]


def test_lista_muestra_badges_de_rol(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: _users())
    cuerpo = client.get("/usuarios").get_data(as_text=True)
    assert "badge--mesero" in cuerpo
    assert "badge--cocinero" in cuerpo


def test_lista_filtra_por_rol(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: _users())
    cuerpo = client.get("/usuarios?rol=Mesero").get_data(as_text=True)
    assert "Eduardo" in cuerpo
    assert "Rafael" not in cuerpo


def test_lista_filtra_por_estado(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: _users())
    cuerpo = client.get("/usuarios?estado=inactivo").get_data(as_text=True)
    assert "Rafael" in cuerpo
    assert "Eduardo" not in cuerpo
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_web_ui.py -k lista -v`
Expected: FAIL — sin `badge--*` y sin filtrado por rol/estado.

- [ ] **Step 3: Añadir filtrado en `web/app/usuarios/routes.py`**

Reemplazar la vista `listar` (actualmente en las líneas del `@bp.route("/usuarios")` / `def listar`) por:

```python
@bp.route("/usuarios")
@login_required
def listar():
    q = request.args.get("q")
    rol = request.args.get("rol") or ""
    estado = request.args.get("estado") or ""
    usuarios = api_gateway.call(api_client.list_usuarios, q)
    if rol:
        usuarios = [u for u in usuarios if u.get("rol", {}).get("nombre_rol") == rol]
    if estado in ("activo", "inactivo"):
        activo = estado == "activo"
        usuarios = [u for u in usuarios if bool(u.get("activo")) == activo]
    return render_template(
        "usuarios/list.html",
        usuarios=usuarios, q=q or "", rol=rol, estado=estado,
        roles=["Administrador", "Cajero", "Cocinero", "Mesero"],
    )
```

- [ ] **Step 4: Reescribir `web/app/templates/usuarios/list.html`**

```html
{% extends "base.html" %}
{% block title %}Usuarios y Roles — Cafetería Aroma{% endblock %}
{% set badge_de = {'Administrador':'admin','Cajero':'cajero','Cocinero':'cocinero','Mesero':'mesero'} %}
{% block content %}
<div class="page-head">
  <div>
    <h1>Usuarios y Roles</h1>
    <p class="sub">{{ usuarios|length }} usuario(s)</p>
  </div>
  <a class="btn btn--accent" href="{{ url_for('usuarios.nuevo') }}">+ Nuevo usuario</a>
</div>

<form method="get" class="toolbar">
  <div class="search">
    <input type="search" name="q" value="{{ q }}" placeholder="Buscar usuario por nombre o correo…">
    <button type="submit">Buscar</button>
  </div>
  <select name="rol" onchange="this.form.submit()">
    <option value="">Rol: Todos</option>
    {% for r in roles %}<option value="{{ r }}" {{ 'selected' if rol == r }}>{{ r }}</option>{% endfor %}
  </select>
  <select name="estado" onchange="this.form.submit()">
    <option value="">Estado: Todos</option>
    <option value="activo" {{ 'selected' if estado == 'activo' }}>Activo</option>
    <option value="inactivo" {{ 'selected' if estado == 'inactivo' }}>Inactivo</option>
  </select>
</form>

<div class="card" style="padding:0;overflow:hidden;">
<table class="table">
  <thead>
    <tr><th>Usuario</th><th>Rol</th><th>Estado</th><th></th></tr>
  </thead>
  <tbody>
  {% for u in usuarios %}
    <tr>
      <td>
        <div class="userline">
          <span class="avatar">{{ (u.nombre[0] ~ u.apellido_paterno[0])|upper }}</span>
          <div>{{ u.nombre }} {{ u.apellido_paterno }}<br><small>{{ u.correo }}</small></div>
        </div>
      </td>
      <td><span class="badge badge--{{ badge_de.get(u.rol.nombre_rol, 'cajero') }}">{{ u.rol.nombre_rol }}</span></td>
      <td>
        <span class="{{ 'state--on' if u.activo else 'state--off' }}">
          <span class="dot {{ 'dot--on' if u.activo else 'dot--off' }}"></span>{{ 'Activo' if u.activo else 'Inactivo' }}
        </span>
      </td>
      <td class="actions">
        <a class="icon-btn" href="{{ url_for('usuarios.editar', id_usuario=u.id_usuario) }}" title="Editar">✎</a>
        {% if u.activo %}
        <form method="post" action="{{ url_for('usuarios.desactivar', id_usuario=u.id_usuario) }}"
              onsubmit="return confirm('¿Desactivar a {{ u.nombre }}?')">
          <button class="link-danger" type="submit" title="Desactivar">Desactivar</button>
        </form>
        {% endif %}
      </td>
    </tr>
  {% else %}
    <tr><td colspan="4" class="muted">Sin usuarios.</td></tr>
  {% endfor %}
  </tbody>
</table>
</div>
{% endblock %}
```

- [ ] **Step 5: Run the list tests + the existing render test**

Run: `docker compose exec web pytest tests/test_web_ui.py tests/test_auth.py::test_usuarios_lista_renderiza -v`
Expected: PASS — badges presentes, filtros acotan, y el test existente (`Ana`/`Mesero`) sigue verde (el mock sin `apellido_materno`/`nombre_usuario` renderiza igual; el avatar usa `nombre[0]`+`apellido_paterno[0]`).

- [ ] **Step 6: Commit**

```bash
git add web/app/usuarios/routes.py web/app/templates/usuarios/list.html \
        web/tests/test_web_ui.py
git commit -m "feat(web): rediseño lista de usuarios con badges y filtros Rol/Estado"
```

---

## Task 5: Nuevo/Editar usuario (dos columnas + permisos)

**Files:**
- Modify: `web/app/templates/usuarios/form.html`
- Test: `web/tests/test_web_ui.py`

**Interfaces:**
- Consumes: contexto de `usuarios.nuevo`/`usuarios.editar` (`roles`, `usuario`, `form`). Sin cambios en la ruta.
- Produces: form de dos columnas — "Datos del usuario" (campos reales) + "Asignar rol" (tarjetas de radio `name="id_rol"`) + "Permisos del rol" (panel informativo con JS por rol).

- [ ] **Step 1: Write the failing test**

Añadir a `web/tests/test_web_ui.py`:

```python
ROLES = [
    {"id_rol": 1, "nombre_rol": "Administrador", "descripcion": None},
    {"id_rol": 3, "nombre_rol": "Cocinero", "descripcion": None},
    {"id_rol": 4, "nombre_rol": "Mesero", "descripcion": None},
]


def test_form_nuevo_tarjetas_rol_y_permisos(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_roles", lambda a: ROLES)
    cuerpo = client.get("/usuarios/nuevo").get_data(as_text=True)
    assert "role-card" in cuerpo
    assert "Permisos del rol" in cuerpo
    assert "Mesero" in cuerpo                 # opción de rol renderizada
    assert 'name="id_rol"' in cuerpo          # el radio conserva el campo real
    assert 'name="nombre_usuario"' in cuerpo  # campo real, no se pierde
```

- [ ] **Step 2: Run test to verify it fails**

Run: `docker compose exec web pytest tests/test_web_ui.py::test_form_nuevo_tarjetas_rol_y_permisos -v`
Expected: FAIL — el form actual usa un `<select>` de rol, sin `role-card` ni panel de permisos.

- [ ] **Step 3: Reescribir `web/app/templates/usuarios/form.html`**

```html
{% extends "base.html" %}
{% block title %}{{ 'Editar' if usuario else 'Nuevo' }} usuario — Cafetería Aroma{% endblock %}
{% block content %}
<div class="page-head">
  <div>
    <h1>{{ 'Editar' if usuario else 'Nuevo' }} usuario</h1>
    <p class="sub">Crea la cuenta y asigna su rol</p>
  </div>
</div>

<form method="post"
      action="{{ url_for('usuarios.actualizar', id_usuario=usuario.id_usuario) if usuario else url_for('usuarios.crear') }}">
<div class="cols">
  <div class="card">
    <h2 class="card__title">Datos del usuario</h2>
    <label>Nombre
      <input name="nombre" value="{{ form.get('nombre', '') }}" required></label>
    <label>Apellido paterno
      <input name="apellido_paterno" value="{{ form.get('apellido_paterno', '') }}" required></label>
    <label>Apellido materno
      <input name="apellido_materno" value="{{ form.get('apellido_materno', '') or '' }}"></label>
    <label>Correo electrónico
      <input type="email" name="correo" value="{{ form.get('correo', '') }}" required></label>
    <label>Nombre de usuario
      <input name="nombre_usuario" value="{{ form.get('nombre_usuario', '') }}" required></label>
    <label>Contraseña {{ '(dejar en blanco para no cambiar)' if usuario else '(mínimo 8 caracteres)' }}
      <input type="password" name="password" id="password" {{ '' if usuario else 'required' }}></label>
    <label class="inline">
      <input type="checkbox" onclick="document.getElementById('password').type = this.checked ? 'text' : 'password'">
      Mostrar contraseña
    </label>
    <div class="header-row" style="margin-top:1rem;">
      <button type="submit">Guardar usuario</button>
      <a class="btn btn--ghost" href="{{ url_for('usuarios.listar') }}">Cancelar</a>
    </div>
  </div>

  <div class="stack">
    <div class="card">
      <h2 class="card__title">Asignar rol</h2>
      <div class="role-cards">
        {% for r in roles %}
        <label class="role-card" data-rol="{{ r.nombre_rol }}">
          <input type="radio" name="id_rol" value="{{ r.id_rol }}"
                 {{ 'checked' if form.get('id_rol')|string == r.id_rol|string else '' }}>
          {{ r.nombre_rol }}
        </label>
        {% endfor %}
      </div>
    </div>
    <div class="card">
      <h2 class="card__title">Permisos del rol</h2>
      <ul class="perms" id="perms"><li class="muted" style="color:var(--muted)">Selecciona un rol</li></ul>
    </div>
  </div>
</div>
</form>

<script>
  const PERMISOS = {
    "Administrador": ["Acceso total al panel", "Gestión de usuarios y roles", "Ver reportes y estadísticas"],
    "Cajero": ["Cobro de pedidos", "Registro de gastos", "Ver ventas del día"],
    "Cocinero": ["Ver pedidos entrantes", "Avanzar estados de cocina", "Registrar inventario"],
    "Mesero": ["Tomar pedidos", "Ver y editar el menú del pedido", "Ver estado de sus pedidos"],
  };
  function pintarPermisos(rol) {
    const ul = document.getElementById("perms");
    const lista = PERMISOS[rol];
    ul.innerHTML = lista ? lista.map(p => "<li>" + p + "</li>").join("")
                         : '<li class="muted">Selecciona un rol</li>';
  }
  document.querySelectorAll('.role-card').forEach(card => {
    const radio = card.querySelector('input');
    radio.addEventListener('change', () => {
      document.querySelectorAll('.role-card').forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      pintarPermisos(card.dataset.rol);
    });
    if (radio.checked) { card.classList.add('selected'); pintarPermisos(card.dataset.rol); }
  });
</script>
{% endblock %}
```

- [ ] **Step 4: Run the form tests (new + existing)**

Run: `docker compose exec web pytest tests/test_web_ui.py::test_form_nuevo_tarjetas_rol_y_permisos tests/test_usuarios.py -v`
Expected: PASS — el nuevo form tiene `role-card`/permisos; `test_form_nuevo_muestra_roles` ("Mesero"), `test_crear_ok_redirige` (campos reales incl. `id_rol`) y `test_crear_correo_duplicado_muestra_error` siguen verdes.

- [ ] **Step 5: Full web suite + smoke manual**

Run: `docker compose exec web pytest`
Expected: PASS (todos).

Luego smoke manual:
```bash
docker compose restart web
```
Con sesión de admin en `localhost:5000`, revisar las 4 pantallas: login (split), Estadísticas (KPIs+gráficas), Usuarios (badges+filtros) y Nuevo usuario (tarjetas de rol + permisos que cambian al elegir rol). Confirmar que el sidebar resalta la página activa y es usable en pantalla angosta.

- [ ] **Step 6: Commit**

```bash
git add web/app/templates/usuarios/form.html web/tests/test_web_ui.py
git commit -m "feat(web): rediseño form de usuario (tarjetas de rol + permisos)"
```

---

## Definition of Done

- Panel web con identidad "Cafetería Aroma": sidebar (Estadísticas + Usuarios y Roles), tema café/ámbar, tipografía serif/mono del sistema.
- Login split (marca + tarjeta "Acceso exclusivo para administradores").
- Estadísticas = dashboard del Slice A re-estilizado (mismos datos/gráficas).
- Usuarios: lista con avatares, badges de rol y filtros Rol/Estado; form de dos columnas con tarjetas de rol y panel de permisos informativo.
- Campos de usuario reales (sin teléfono). Sin cambios de backend/API ni migraciones.
- Suite web en verde (`docker compose exec web pytest`); smoke manual tras `docker compose restart web`.
- Fuera de alcance (su propio slice): Reportes + export (Slice B) y analítica avanzada (dona, % vs mes anterior, nivel de inventario, tendencia diaria).
```
