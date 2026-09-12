import pytest
import re
from fastapi import FastAPI, Depends
from fastapi.responses import HTMLResponse
from app.main import app
from app.models import User, UserRole
from app.dependencies import (
    get_current_user_web,
    require_roles_web,
    generate_csrf_token,
    validate_csrf_token,
    is_safe_url
)


def extract_csrf_token(html_text: str) -> str:
    """Helper to extract csrf_token value from rendered HTML form."""
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text)
    if not match:
        match = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', html_text)
    assert match is not None, "CSRF token not found in HTML response"
    return match.group(1)


def test_root_route_redirects_to_login(client):
    """Verify GET / returns HTTP 303 with Location: /login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login"


def test_root_route_follow_redirects_reaches_login(client):
    """Verify GET / with follow_redirects=True successfully resolves at /login."""
    response = client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert "Account Sign In" in response.text
    assert "csrf_token" in response.text


def test_get_login_page_renders_html(client):
    """Verify GET /login returns 200 with HTML content and embedded CSRF token."""
    response = client.get("/login")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Account Sign In" in response.text
    assert "csrf_token" in response.text
    token = extract_csrf_token(response.text)
    assert validate_csrf_token(token) is True


def test_static_css_served(client):
    """Verify static CSS stylesheet is accessible."""
    response = client.get("/static/css/styles.css")
    assert response.status_code == 200
    assert "text/css" in response.headers.get("content-type", "")


def test_web_login_success_establishes_session(client, admin_user):
    """Verify valid credentials establish crm_session cookie and redirect."""
    # 1. Fetch login page to get CSRF token
    get_res = client.get("/login")
    csrf_token = extract_csrf_token(get_res.text)

    # 2. Submit valid credentials
    post_res = client.post(
        "/login",
        data={
            "username_or_email": admin_user.username,
            "password": "AdminPass123!",
            "csrf_token": csrf_token
        },
        follow_redirects=False
    )
    assert post_res.status_code == 303
    assert post_res.headers.get("location") == "/dashboard"
    assert "crm_session" in post_res.cookies
    cookie_header = post_res.headers.get("set-cookie", "").lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header


def test_web_login_invalid_credentials_returns_safe_error(client, admin_user):
    """Verify invalid credentials return 401 HTML with generic error and no session cookie."""
    get_res = client.get("/login")
    csrf_token = extract_csrf_token(get_res.text)

    post_res = client.post(
        "/login",
        data={
            "username_or_email": admin_user.username,
            "password": "WrongPassword123!",
            "csrf_token": csrf_token
        },
        follow_redirects=False
    )
    assert post_res.status_code == 401
    assert "text/html" in post_res.headers.get("content-type", "")
    assert "Invalid username/email or password." in post_res.text
    assert "crm_session" not in post_res.cookies


def test_web_login_nonexistent_user_returns_generic_error(client):
    """Verify nonexistent user login does not enumerate user accounts."""
    get_res = client.get("/login")
    csrf_token = extract_csrf_token(get_res.text)

    post_res = client.post(
        "/login",
        data={
            "username_or_email": "nonexistent_user_9999@example.com",
            "password": "RandomPassword123!",
            "csrf_token": csrf_token
        },
        follow_redirects=False
    )
    assert post_res.status_code == 401
    assert "Invalid username/email or password." in post_res.text
    assert "crm_session" not in post_res.cookies


def test_web_login_inactive_user_failure(client, inactive_user):
    """Verify inactive user cannot log in via Web UI."""
    get_res = client.get("/login")
    csrf_token = extract_csrf_token(get_res.text)

    post_res = client.post(
        "/login",
        data={
            "username_or_email": inactive_user.username,
            "password": "InactivePass123!",
            "csrf_token": csrf_token
        },
        follow_redirects=False
    )
    assert post_res.status_code == 401
    assert "Invalid username/email or password." in post_res.text
    assert "crm_session" not in post_res.cookies


def test_web_login_csrf_failure(client, admin_user):
    """Verify login fails if CSRF token is invalid or tampered."""
    post_res = client.post(
        "/login",
        data={
            "username_or_email": admin_user.username,
            "password": "AdminPass123!",
            "csrf_token": "tampered-csrf-token-12345"
        },
        follow_redirects=False
    )
    assert post_res.status_code == 400
    assert "Invalid or expired security token" in post_res.text
    assert "crm_session" not in post_res.cookies


def test_safe_return_url_redirect(client, admin_user):
    """Verify valid relative return URL (?next=) is followed on successful login."""
    get_res = client.get("/login?next=/some-internal-path")
    csrf_token = extract_csrf_token(get_res.text)

    post_res = client.post(
        "/login",
        data={
            "username_or_email": admin_user.username,
            "password": "AdminPass123!",
            "csrf_token": csrf_token,
            "next": "/some-internal-path"
        },
        follow_redirects=False
    )
    assert post_res.status_code == 303
    assert post_res.headers.get("location") == "/some-internal-path"


def test_open_redirect_attempts_rejected(client, admin_user):
    """Verify external, scheme-relative, and backslash open redirect vectors are rejected."""
    malicious_targets = [
        "http://evil.example.com",
        "https://attacker.org/steal",
        "//evil.example.com",
        r"/\evil.example.com",
        "javascript:alert(1)",
        "data:text/html,evil"
    ]

    for target in malicious_targets:
        get_res = client.get(f"/login?next={target}")
        csrf_token = extract_csrf_token(get_res.text)

        post_res = client.post(
            "/login",
            data={
                "username_or_email": admin_user.username,
                "password": "AdminPass123!",
                "csrf_token": csrf_token,
                "next": target
            },
            follow_redirects=False
        )
        assert post_res.status_code == 303
        # Should fallback to default safe destination ("/dashboard")
        assert post_res.headers.get("location") == "/dashboard"


def test_protected_web_dependency_redirects_unauthenticated(client):
    """Verify get_current_user_web redirects unauthenticated requests to /login."""
    @app.get("/test-protected-web-route")
    def dummy_protected_route(current_user: User = Depends(get_current_user_web)):
        return {"user": current_user.username}

    response = client.get("/test-protected-web-route", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login?next=/test-protected-web-route"


def test_logout_requires_post(client):
    """Verify GET /logout returns 405 Method Not Allowed."""
    response = client.get("/logout")
    assert response.status_code == 405


def test_logout_requires_valid_csrf(auth_client, admin_user):
    """Verify POST /logout rejects requests without valid CSRF token."""
    response = auth_client.post("/logout", data={"csrf_token": "bad-token"}, follow_redirects=False)
    assert response.status_code == 400


def test_valid_logout_clears_cookie_and_redirects(auth_client, admin_user):
    """Verify valid POST /logout clears crm_session cookie and redirects to /login."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post("/logout", data={"csrf_token": csrf_token}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login"
    
    # Verify cookie deletion header
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "crm_session=" in set_cookie_header


def test_rest_api_auth_remains_unchanged(client):
    """Verify REST API endpoints continue returning 401 JSON and are not redirected."""
    response = client.get("/api/v1/leads")
    assert response.status_code == 401
    assert "application/json" in response.headers.get("content-type", "")
    data = response.json()
    assert "detail" in data
    assert "Authentication credentials required." in data["detail"]


def test_rest_api_usable_without_csrf(auth_client):
    """Verify REST API endpoints do not require Web CSRF tokens."""
    payload = {
        "first_name": "API",
        "last_name": "Lead",
        "email": "apilead@example.com",
        "company_name": "API Corp"
    }
    response = auth_client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201


def test_require_roles_web_authorization(client, rep_user):
    """Verify require_roles_web enforces role restrictions in Web routes."""
    from app.services.auth_service import create_access_token
    from app.config import settings

    @app.get("/test-admin-web-route")
    def dummy_admin_route(current_user: User = Depends(require_roles_web(UserRole.ADMIN))):
        return {"admin": True}

    token = create_access_token(rep_user)
    client.cookies.set(settings.COOKIE_NAME, token)

    response = client.get("/test-admin-web-route")
    assert response.status_code == 403
    assert "insufficient role permissions" in response.text.lower()


def test_is_safe_url_unit():
    """Unit test for is_safe_url helper."""
    assert is_safe_url("/dashboard") is True
    assert is_safe_url("/leads?page=1&size=10") is True
    assert is_safe_url("/login") is True
    assert is_safe_url(None) is False
    assert is_safe_url("") is False
    assert is_safe_url("http://example.com") is False
    assert is_safe_url("//example.com") is False
    assert is_safe_url(r"/\example.com") is False
    assert is_safe_url("javascript:void(0)") is False


def test_openapi_schema_excludes_browser_routes(client):
    """Verify browser Web UI routes are excluded from /openapi.json schema."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})

    # Browser Web UI routes must NOT appear in OpenAPI schema
    assert "/" not in paths
    assert "/login" not in paths
    assert "/logout" not in paths


def test_openapi_schema_retains_rest_api_routes(client):
    """Verify programmatic REST API endpoints remain present in /openapi.json."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})

    # REST API and Health routes MUST appear in OpenAPI schema
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/leads" in paths
    assert "/api/v1/leads/{lead_id}" in paths
    assert "/health" in paths
