import os
import pytest
from app.config import Settings


def test_default_settings_resolution():
    settings = Settings()
    assert settings.APP_NAME == "Business CRM Lead Management API"
    assert settings.ENVIRONMENT == "development"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert "sqlite" in settings.DATABASE_URL
    assert settings.SECRET_KEY != ""


def test_custom_environment_variable_override(monkeypatch):
    monkeypatch.setenv("APP_NAME", "Custom CRM Test Name")
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("SECRET_KEY", "dummy_test_secret_12345")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")

    custom_settings = Settings()
    assert custom_settings.APP_NAME == "Custom CRM Test Name"
    assert custom_settings.ENVIRONMENT == "testing"
    assert custom_settings.SECRET_KEY == "dummy_test_secret_12345"
    assert custom_settings.CORS_ORIGINS == ["http://localhost:3000", "http://localhost:8000"]


def test_cors_origins_json_list_parsing(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://example.com", "https://app.example.com"]')
    custom_settings = Settings()
    assert custom_settings.CORS_ORIGINS == ["https://example.com", "https://app.example.com"]


def test_no_secret_leak_in_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    res_text = response.text.lower()
    assert "secret" not in res_text
    assert "password" not in res_text
    assert "token" not in res_text
