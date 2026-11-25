import pytest

from app import create_app
from app.config import ProductionConfig, get_config


def test_testing_config_is_used(app):
    assert app.config["TESTING"] is True
    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite:///:memory:"


def test_unknown_config_name_fails():
    with pytest.raises(ValueError):
        get_config("staging")


def test_missing_app_env_means_production(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    assert get_config() is ProductionConfig


def test_production_never_allows_the_dev_admin_header():
    assert ProductionConfig.ALLOW_DEV_AUTH is False
    assert not getattr(ProductionConfig, "DEBUG", False)


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
    # assert "/api/v1/rooms" in spec["paths"]
    # assert "/api/v1/availability" in spec["paths"]


def test_unknown_url_returns_json_404(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.get_json()["error"] == "Not Found"
