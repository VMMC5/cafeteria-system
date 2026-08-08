import re
from pathlib import Path

import pytest

from app import create_app
from app.services import api_client

PLANTILLAS = Path(__file__).resolve().parents[1] / "app" / "templates"


def test_toda_plantilla_con_post_lleva_csrf_token():
    """Cada <form method="post"> debe emitir su propio campo csrf_token.

    Se comprueba por formulario, no por archivo: un conteo agregado
    ("aparece csrf_token al menos tantas veces como method=\"post\"") puede
    pasar con un formulario genuinamente desprotegido si el archivo tiene
    alguna otra ocurrencia de la subcadena "csrf_token" (un comentario, una
    cadena en JS, etc.) que infle el total, y tampoco distingue si el token
    cayó dentro o fuera del bucle que repite el formulario. Extraer cada
    bloque <form>…</form> y exigir el token dentro de sus propios límites
    ata el chequeo a la estructura real en vez de a un conteo global.
    """
    faltantes = []
    for archivo in sorted(PLANTILLAS.rglob("*.html")):
        texto = archivo.read_text(encoding="utf-8")
        for formulario in re.findall(r"<form\b.*?</form>", texto, re.S):
            if 'method="post"' not in formulario:
                continue
            if "csrf_token" not in formulario:
                accion = re.search(r'action="([^"]*)"', formulario)
                detalle = accion.group(1) if accion else formulario[:60]
                faltantes.append(
                    f"{archivo.relative_to(PLANTILLAS).as_posix()} (action={detalle})"
                )
    assert faltantes == []


def test_login_renderiza_un_token_real(client):
    """El campo no basta con existir en la plantilla: debe salir con valor."""
    cuerpo = client.get("/login").get_data(as_text=True)
    assert 'name="csrf_token"' in cuerpo
    assert 'value=""' not in cuerpo


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
