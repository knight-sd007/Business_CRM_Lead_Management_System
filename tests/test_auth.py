import pytest
from app.config import settings
from app.models import User, UserRole
from app.services.auth_service import hash_password, verify_password, AuthService


def test_password_hashing_and_verification():
    raw_pass = "SuperSecretPassword123!"
    hashed = hash_password(raw_pass)

    assert hashed != raw_pass
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_public_unauthenticated_registration_rejected(client):
    """Verify unauthenticated callers cannot create accounts (public registration is disabled)."""
    payload = {
        "email": "intruder@example.com",
        "username": "intruder",
        "full_name": "Intruder User",
        "password": "IntruderPassword123!",
        "role": "admin"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 401
    assert "authentication credentials required" in response.json()["detail"].lower()


def test_sales_rep_cannot_register_users(rep_client):
    """Verify non-admin users (e.g. Sales Reps) cannot create or escalate accounts."""
    payload = {
        "email": "subordinate@example.com",
        "username": "subordinate",
        "full_name": "Subordinate User",
        "password": "Password123!",
        "role": "rep"
    }
    response = rep_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 403
    assert "insufficient role permissions" in response.json()["detail"].lower()


def test_admin_user_registration_success(auth_client):
    """Verify authenticated administrators can register and assign roles to new CRM users."""
    payload = {
        "email": "newrep@crm.example.com",
        "username": "newrep",
        "full_name": "New Sales Rep",
        "password": "StrongRepPassword123!",
        "role": "rep"
    }
    response = auth_client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newrep@crm.example.com"
    assert data["username"] == "newrep"
    assert data["role"] == "rep"
    assert data["full_name"] == "New Sales Rep"
    assert "password" not in data
    assert "password_hash" not in data
    assert "id" in data


def test_duplicate_registration_rejected(auth_client, admin_user):
    # Duplicate email
    res1 = auth_client.post("/api/v1/auth/register", json={
        "email": admin_user.email,
        "username": "distinct_user",
        "full_name": "Distinct User",
        "password": "Password123!"
    })
    assert res1.status_code == 400
    assert "email" in res1.json()["detail"].lower()

    # Duplicate username
    res2 = auth_client.post("/api/v1/auth/register", json={
        "email": "distinct_email@example.com",
        "username": admin_user.username,
        "full_name": "Distinct User",
        "password": "Password123!"
    })
    assert res2.status_code == 400
    assert "username" in res2.json()["detail"].lower()


def test_login_success_sets_session_cookie_without_token_exposure(client, admin_user):
    """Verify login sets HTTP-only cookie and does NOT expose access_token in response JSON."""
    login_payload = {
        "username_or_email": admin_user.username,
        "password": "AdminPass123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()

    # Verify no access_token is leaked in the response body
    assert "access_token" not in data
    assert "token" not in data
    assert data["message"] == "Authentication successful"
    assert data["user"]["email"] == admin_user.email
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify secure HTTP-only session cookie is set
    assert settings.COOKIE_NAME in response.cookies
    session_cookie = response.cookies[settings.COOKIE_NAME]
    assert len(session_cookie) > 20


def test_login_with_email_success(client, admin_user):
    login_payload = {
        "username_or_email": admin_user.email,
        "password": "AdminPass123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    assert settings.COOKIE_NAME in response.cookies


def test_login_invalid_password_failure(client, admin_user):
    login_payload = {
        "username_or_email": admin_user.username,
        "password": "IncorrectPassword!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


def test_login_nonexistent_user_failure(client):
    login_payload = {
        "username_or_email": "nonexistent@example.com",
        "password": "SomePassword123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401


def test_login_inactive_user_failure(client, inactive_user):
    login_payload = {
        "username_or_email": inactive_user.username,
        "password": "InactivePass123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "inactive" in response.json()["detail"].lower()


def test_logout_clears_cookie(auth_client):
    response = auth_client.post("/api/v1/auth/logout")
    assert response.status_code == 200
    assert response.json()["detail"] == "Successfully logged out."


def test_get_current_user_profile_cookie_auth(auth_client, admin_user):
    response = auth_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == admin_user.id
    assert data["email"] == admin_user.email
    assert data["role"] == "admin"


def test_get_current_user_unauthenticated_failure(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_bootstrap_admin_creation_and_idempotency(test_db):
    """Verify bootstrap admin creation is safe, sets ADMIN role, and is idempotent."""
    auth_service = AuthService(test_db)

    # 1. Initial bootstrap
    admin = auth_service.bootstrap_admin_user(
        email="bootstrap.admin@example.com",
        username="bootstrap_admin",
        password="BootstrapPassword123!",
        full_name="Initial Bootstrap Admin"
    )
    assert admin is not None
    assert admin.email == "bootstrap.admin@example.com"
    assert admin.role == UserRole.ADMIN
    assert admin.is_active is True
    assert verify_password("BootstrapPassword123!", admin.password_hash) is True

    # 2. Repeated bootstrap attempt should return None and not duplicate
    repeated = auth_service.bootstrap_admin_user(
        email="bootstrap.admin@example.com",
        username="bootstrap_admin",
        password="AnotherPassword123!"
    )
    assert repeated is None
