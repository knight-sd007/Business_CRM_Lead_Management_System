import pytest
from app.config import Settings


def test_sql_injection_resilience(auth_client):
    # Attempt SQL injection payloads in search query parameter
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE leads; --",
        "1 UNION SELECT 1,2,3,4,5--",
        "admin'--"
    ]
    for payload in sql_payloads:
        response = auth_client.get(f"/api/v1/leads?search={payload}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)


def test_path_traversal_resilience(auth_client):
    traversal_paths = [
        "/api/v1/leads/../../etc/passwd",
        "/api/v1/leads/..%2f..%2fetc%2fpasswd",
        "/api/v1/leads/windows/system32"
    ]
    for path in traversal_paths:
        response = auth_client.get(path)
        assert response.status_code in (404, 400, 422)


def test_500_error_suppresses_stack_trace(auth_client, monkeypatch):
    # Simulate an unexpected exception in lead service
    def mock_get_lead_raise(*args, **kwargs):
        raise RuntimeError("Database connection string postgresql://user:secret123@db:5432/crm_db unexpected failure")

    monkeypatch.setattr("app.services.lead_service.LeadService.get_lead", mock_get_lead_raise)

    response = auth_client.get("/api/v1/leads/some-id-123")
    assert response.status_code == 500
    data = response.json()
    assert data["detail"] == "An internal server error occurred."
    assert "secret123" not in response.text
    assert "postgresql://" not in response.text
    assert "RuntimeError" not in response.text


def test_cors_headers_response(client):
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


def test_csv_formula_injection_mitigation(auth_client):
    """
    Verify dangerous formula characters ('=', '+', '-', '@', '\t', '\r')
    are safely prefixed with a single quote (') during CSV export.
    """
    # 1. Create lead with formula injection attack payloads
    malicious_payload = {
        "first_name": "=cmd|' /C calc'!A0",
        "last_name": "+1+2",
        "email": "attacker@example.com",
        "company_name": "-2+3*cmd",
        "job_title": "@SUM(1,1)",
        "industry": "Technology",
        "assigned_owner": "\t=1+1"
    }
    create_res = auth_client.post("/api/v1/leads", json=malicious_payload)
    assert create_res.status_code == 201

    # 2. Create legitimate lead without formula prefixes
    legit_payload = {
        "first_name": "Alexander",
        "last_name": "Hamilton",
        "email": "alex@treasury.example.com",
        "company_name": "Treasury Corp",
        "job_title": "Secretary",
        "industry": "Finance",
        "assigned_owner": "Jordan Lee"
    }
    legit_res = auth_client.post("/api/v1/leads", json=legit_payload)
    assert legit_res.status_code == 201

    # 3. Export CSV and inspect raw text
    csv_res = auth_client.get("/api/v1/leads/export/csv")
    assert csv_res.status_code == 200
    csv_text = csv_res.text

    # Verify sanitized malicious fields
    assert "'=cmd|' /C calc'!A0" in csv_text
    assert "'+1+2" in csv_text
    assert "'-2+3*cmd" in csv_text
    assert "'@SUM(1,1)" in csv_text
    assert "'\t=1+1" in csv_text

    # Verify legitimate fields remain unaltered
    assert "Alexander,Hamilton,alex@treasury.example.com,Treasury Corp,Secretary,Finance" in csv_text


def test_production_cors_wildcard_fails_closed(monkeypatch):
    """In production mode, wildcard CORS origin '*' must raise a configuration error."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "strong_production_secret_key_minimum_32_characters_long_12345")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    with pytest.raises(ValueError, match="Wildcard CORS origin"):
        Settings()


def test_production_weak_secret_key_fails_closed(monkeypatch):
    """In production mode, default or short SECRET_KEY must raise a configuration error."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("SECRET_KEY", "default_secret_key_for_dev_only")

    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY"):
        Settings()

    monkeypatch.setenv("SECRET_KEY", "short_key")
    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY"):
        Settings()
