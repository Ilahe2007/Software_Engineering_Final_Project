"""Configuration classes, one per environment.

create_app() picks one of these by name ("development", "testing",
"production"). If no name is given it reads the APP_ENV environment variable.

If APP_ENV is missing too, the app starts in PRODUCTION mode. A deployment that
forgets the variable then fails safely instead of running with the development
shortcuts (debug mode, the development secret key) switched on.
"""
import os

# Only for local development. It is public on purpose: create_app() refuses to start in production with it.
DEV_SECRET_KEY = "dev-only-change-me-this-key-is-public"  # nosec B105


def _database_url(default=None):
    url = os.environ.get("DATABASE_URL", default)
    # Render and Heroku give "postgres://", but SQLAlchemy wants "postgresql://".
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class BaseConfig:
    # Signs the login tokens (JWT, HS256). Anyone who knows it can log in as anyone.
    SECRET_KEY = os.environ.get("SECRET_KEY", DEV_SECRET_KEY)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Rooms can be used between these hours. Free slots are computed inside this window.
    OPENING_HOUR = int(os.environ.get("OPENING_HOUR", 8))
    CLOSING_HOUR = int(os.environ.get("CLOSING_HOUR", 20))

    # Login (Part B). A token stops working after this many minutes; the user logs in again.
    JWT_ACCESS_MINUTES = int(os.environ.get("JWT_ACCESS_MINUTES", 60))
    # Brute-force protection: this many wrong passwords in a row lock the account for LOCKOUT_MINUTES.
    MAX_FAILED_LOGINS = int(os.environ.get("MAX_FAILED_LOGINS", 5))
    LOCKOUT_MINUTES = int(os.environ.get("LOCKOUT_MINUTES", 15))

    SWAGGER = {
        "title": "University Room Management API",
        "uiversion": 3,
        "specs_route": "/docs/",
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "in": "header",
                "name": "Authorization",
                "description": "Log in with POST /api/v1/auth/login, then type: Bearer <access_token>",
            }
        },
    }


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _database_url("sqlite:///dev.db")


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "testing-only-secret-key-at-least-32-bytes"  # nosec B105


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
