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


def test_shell_tiene_enlace_salir(client, monkeypatch):
    _login(client, monkeypatch)
    monkeypatch.setattr(api_client, "list_usuarios", lambda a, q=None: [])
    cuerpo = client.get("/usuarios").get_data(as_text=True)
    assert "/logout" in cuerpo       # href de cierre de sesión
    assert "Salir" in cuerpo          # texto del enlace


def test_login_usa_layout_publico_sin_sidebar(client):
    cuerpo = client.get("/login").get_data(as_text=True)
    assert "Iniciar" in cuerpo
    assert 'class="sidebar"' not in cuerpo              # el login no muestra sidebar


def test_login_split_marca_y_subtitulo(client):
    cuerpo = client.get("/login").get_data(as_text=True)
    assert "login__brand" in cuerpo
    assert "Aroma" in cuerpo                                  # marca completa
    assert "Acceso exclusivo para administradores" in cuerpo  # subtítulo del card
    assert "Ingresar" in cuerpo                               # botón
