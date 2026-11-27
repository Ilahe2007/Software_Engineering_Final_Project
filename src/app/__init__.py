"""Application Factory.

Design pattern: Factory. create_app(config_name) builds a fresh, fully wired
Flask app from a config. Tests call create_app("testing") to get an isolated
app with an in-memory database; run.py and Docker call create_app() and get
the config named by APP_ENV (production if it is not set).
"""
from flask import Flask

from . import auth
from .config import DEV_SECRET_KEY, get_config
from .errors import register_error_handlers
from .extensions import db, swagger

# HS256 needs a key at least as long as its 256-bit output (RFC 7518, section 3.2).
MIN_SECRET_KEY_BYTES = 32


def create_app(config_name=None):
    app = Flask(__name__)
    config = get_config(config_name)
    app.config.from_object(config)

    if config.__name__ == "ProductionConfig":
        _check_production_settings(app)

    db.init_app(app)
    swagger.init_app(app)
    register_error_handlers(app)
    auth.init_app(app)

    # Other modules (Part B bookings, Part C imported lectures/exams) add their
    # busy-time sources here. See app/availability/sources.py.
    app.extensions["busy_sources"] = []

    _register_blueprints(app)

    with app.app_context():
        from . import models  # noqa: F401  (registers the tables)

        # Until Part C adds migrations (Flask-Migrate/Alembic), create tables directly.
        db.create_all()

    return app


def _register_blueprints(app):
    # from .availability import bp as availability_bp
    from .auth import bp as auth_bp
    from .main import bp as main_bp
    from .rooms import bp as rooms_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(rooms_bp, url_prefix="/api/v1")
    # app.register_blueprint(availability_bp, url_prefix="/api/v1")
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    # Part B: app.register_blueprint(bookings_bp, url_prefix="/api/v1")
    # Part D: app.register_blueprint(schedule_bp, url_prefix="/api/v1/admin/schedule")
    # Part E: app.register_blueprint(notifications_bp, url_prefix="/api/v1")


def _check_production_settings(app):
    hint = " For local development run: python src/run.py --dev"
    if not app.config.get("SQLALCHEMY_DATABASE_URI"):
        raise RuntimeError("DATABASE_URL must be set in production." + hint)
    if app.config["SECRET_KEY"] == DEV_SECRET_KEY:
        raise RuntimeError("SECRET_KEY must be set in production." + hint)
    if len(app.config["SECRET_KEY"].encode()) < MIN_SECRET_KEY_BYTES:
        raise RuntimeError(
            f"SECRET_KEY must be at least {MIN_SECRET_KEY_BYTES} bytes. "
            'Generate one with: python -c "import secrets; print(secrets.token_hex(32))"'
        )
