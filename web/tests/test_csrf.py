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
