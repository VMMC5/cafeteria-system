import re
from pathlib import Path

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
