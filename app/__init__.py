import os
import secrets
from pathlib import Path

from flask import Flask, abort, request, session
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message_category = "info"


def create_app():
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(__name__, template_folder=str(project_root / "templates"),
                static_folder=str(project_root / "static"))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///../data/cases.sqlite"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = str(project_root / "data" / "uploads")
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    @app.context_processor
    def inject_csrf_token():
        def csrf_token():
            if "csrf_token" not in session:
                session["csrf_token"] = secrets.token_urlsafe(32)
            return session["csrf_token"]
        return {"csrf_token": csrf_token}

    @app.before_request
    def protect_forms():
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            supplied = request.form.get("csrf_token", "")
            if not supplied or not secrets.compare_digest(supplied, session.get("csrf_token", "")):
                abort(400, description="Invalid form token. Reload the page and try again.")

    from app.models import User, Case, CaseImage
    from app.auth import auth
    from app.cases import cases
    from app.main import main

    app.register_blueprint(auth)
    app.register_blueprint(cases, url_prefix="/cases")
    app.register_blueprint(main)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    with app.app_context():
        db.create_all()
        case_columns = {column["name"] for column in inspect(db.engine).get_columns("case")}
        if "missing_since" not in case_columns:
            db.session.execute(text('ALTER TABLE "case" ADD COLUMN missing_since DATE'))
            db.session.commit()
            case_columns.add("missing_since")
        if "closed_at" not in case_columns:
            db.session.execute(text('ALTER TABLE "case" ADD COLUMN closed_at DATE'))
        if "closure_note" not in case_columns:
            db.session.execute(text('ALTER TABLE "case" ADD COLUMN closure_note VARCHAR(500)'))
        image_columns = {column["name"] for column in inspect(db.engine).get_columns("case_image")}
        if "subject_age" not in image_columns:
            db.session.execute(text('ALTER TABLE "case_image" ADD COLUMN subject_age INTEGER'))
        db.session.commit()

    return app
