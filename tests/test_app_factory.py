import pytest

from app import create_app
from app.config import DEV_SECRET_KEY, ProductionConfig, get_config


def test_testing_config_is_used(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_unknown_config_name_fails():
    with pytest.raises(ValueError):
        get_config("staging")


def test_missing_app_env_means_production(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert get_config() is ProductionConfig


def test_production_is_not_in_debug_mode():
    assert not getattr(ProductionConfig, "DEBUG", False)


def test_the_old_dev_role_header_no_longer_gives_admin_rights(client):
    body = {"name": "lab"}
    assert client.post("/api/v1/room-types", json=body, headers={"X-User-Role": "admin"}).status_code == 401


def test_production_refuses_the_development_secret_key(monkeypatch):
    # Config values are read from the environment at import time, so patch the class itself.
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", DEV_SECRET_KEY)
    with pytest.raises(RuntimeError, match="SECRET_KEY must be set"):
        create_app("production")


def test_production_refuses_a_short_secret_key(monkeypatch):
    monkeypatch.setattr(ProductionConfig, "SQLALCHEMY_DATABASE_URI", "sqlite://")
    monkeypatch.setattr(ProductionConfig, "SECRET_KEY", "too-short")
    with pytest.raises(RuntimeError, match="at least 32 bytes"):
        create_app("production")


def test_production_refuses_to_start_without_secrets(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError):
        create_app("production")


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "database": "ok"}


def test_swagger_docs_are_served(client):
    assert client.get("/docs/").status_code == 200
    spec = client.get("/apispec_1.json").get_json()
    assert "/api/v1/rooms" in spec["paths"]
    # assert "/api/v1/availability" in spec["paths"]


def test_unknown_url_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not Found"
