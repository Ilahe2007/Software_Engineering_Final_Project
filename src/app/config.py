"""Configuration classes, one per environment.

create_app() picks one of these by name ("development", "testing",
"production"). If no name is given it reads the APP_ENV environment variable.

If APP_ENV is missing too, the app starts in PRODUCTION mode. A deployment that
forgets the variable then fails safely instead of running with the development
shortcuts (header-based admin, debug mode) switched on.
"""
import os


def _database_url(default=None):
    url = os.environ.get("DATABASE_URL", default)
    # Render and Heroku give "postgres://", but SQLAlchemy wants "postgresql://".
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Rooms can be used between these hours. Free slots are computed inside this window.
    OPENING_HOUR = int(os.environ.get("OPENING_HOUR", 8))
    CLOSING_HOUR = int(os.environ.get("CLOSING_HOUR", 20))

    # Temporary header-based auth until Part B ships real login. Never on in production.
    ALLOW_DEV_AUTH = False

    SWAGGER = {
        "title": "University Room Management API",
        "uiversion": 3,
        "specs_route": "/docs/",
        "securityDefinitions": {
            "DevRole": {
                "type": "apiKey",
                "in": "header",
                "name": "X-User-Role",
                "description": "Temporary: type 'admin' to call admin endpoints (dev/test only).",
            }
        },
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _database_url("sqlite:///dev.db")
    ALLOW_DEV_AUTH = True


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    ALLOW_DEV_AUTH = True


class ProductionConfig(BaseConfig):
    SQLALCHEMY_DATABASE_URI = _database_url()


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config(name=None):
    name = name or os.environ.get("APP_ENV", "production")
    try:
        return CONFIGS[name]
    except KeyError:
        raise ValueError(f"Unknown config '{name}'. Use one of: {', '.join(CONFIGS)}")
