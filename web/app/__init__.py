from flask import Flask


def create_app():
    """App factory del panel admin (Flask)."""
    app = Flask(__name__)

    @app.get("/")
    def index():
        return "Hola mundo — Panel Admin Cafetería (Sprint 0)"

    return app
