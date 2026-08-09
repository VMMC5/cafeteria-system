import os


class Config:
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret")
    API_BASE_URL = os.environ.get("API_BASE_URL", "http://api:8000/api/v1")
    # El token CSRF sigue atado a la sesión (que dura todo el navegador), así
    # que quitarle el límite de una hora no debilita la protección: solo
    # evita que un formulario abierto y retomado más tarde (ej. "Nuevo
    # producto" interrumpido) sea rechazado y pierda todos sus campos.
    WTF_CSRF_TIME_LIMIT = None
