from flask import Flask, redirect, url_for
from flask_login import LoginManager

from app.auth import load_user_from_session
from app.config import Config
from app.services.api_gateway import ReloginRequired

login_manager = LoginManager()
login_manager.login_view = "auth.login"


def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    login_manager.init_app(app)

    @login_manager.user_loader
    def _loader(user_id):
        return load_user_from_session()

    from app.auth.routes import bp as auth_bp
    from app.usuarios.routes import bp as usuarios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)

    @app.route("/")
    def index():
        return redirect(url_for("usuarios.listar"))

    @app.errorhandler(ReloginRequired)
    def _relogin(_e):
        return redirect(url_for("auth.login"))

    return app
