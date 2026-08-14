import pytest


def test_sql_injection_resilience(client):
    # Attempt SQL injection payloads in search query parameter
    sql_payloads = [
        "' OR '1'='1",
        "'; DROP TABLE leads; --",
        "1 UNION SELECT 1,2,3,4,5--",
        "admin'--"
    ]
    for payload in sql_payloads:
        response = client.get(f"/api/v1/leads?search={payload}")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert isinstance(data["items"], list)


def test_path_traversal_resilience(client):
    traversal_paths = [
        "/api/v1/leads/../../etc/passwd",
        "/api/v1/leads/..%2f..%2fetc%2fpasswd",
        "/api/v1/leads/windows/system32"
    ]
    for path in traversal_paths:
        response = client.get(path)
        assert response.status_code in (404, 400, 422)


def test_500_error_suppresses_stack_trace(client, monkeypatch):
    # Simulate an unexpected exception in lead service
    def mock_get_lead_raise(*args, **kwargs):
        raise RuntimeError("Database connection string postgresql://user:secret123@db:5432/crm_db unexpected failure")

    monkeypatch.setattr("app.services.lead_service.LeadService.get_lead", mock_get_lead_raise)

    response = client.get("/api/v1/leads/some-id-123")
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
