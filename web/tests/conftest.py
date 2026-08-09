import pytest

from app import create_app


@pytest.fixture()
def app():
    app = create_app()
    # Los 26 client.post del suite no mandan token; la protección se prueba
    # a propósito en test_csrf.py, que levanta su propia app con CSRF activo.
    app.config.update(TESTING=True, SECRET_KEY="test", WTF_CSRF_ENABLED=False)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()
