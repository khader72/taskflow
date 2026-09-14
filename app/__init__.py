import os

from flask import Flask

from .db import init_db
from .auth import auth_bp
from .tasks import tasks_bp


def create_app():
    app = Flask(__name__)

    # F3 (intentional): a hardcoded fallback secret. In an earlier commit the key was
    # written directly here (see Git history). Fixed in Module 10: require the env var,
    # remove the fallback, and rotate the key.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-please-change")
    app.config["DATABASE"] = os.environ.get("DATABASE", "taskflow.db")

    init_db(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(tasks_bp)

    @app.get("/")
    def index():
        # Frontend statique (interface web de TaskFlow), servi depuis app/static/.
        # Consomme l'API JSON existante ; ne modifie aucune route ni logique metier.
        return app.send_static_file("index.html")

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
