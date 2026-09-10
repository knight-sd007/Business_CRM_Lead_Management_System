import pytest
from app.config import settings
from app.models import User, UserRole
from app.services.auth_service import hash_password, verify_password, create_access_token


def test_password_hashing_and_verification():
    raw_pass = "SuperSecretPassword123!"
    hashed = hash_password(raw_pass)

    assert hashed != raw_pass
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pass, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_user_registration_success(client):
    payload = {
        "email": "newuser@example.com",
        "username": "newuser",
        "full_name": "New Test User",
        "password": "StrongPassword123!",
        "role": "rep"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["username"] == "newuser"
    assert data["full_name"] == "New Test User"
    assert "password" not in data
    assert "password_hash" not in data
    assert "id" in data


def test_first_registered_user_becomes_admin(client):
    # When no users exist, first registration automatically assigns ADMIN role
    payload = {
        "email": "first_admin@example.com",
        "username": "first_admin",
        "full_name": "First Admin",
        "password": "AdminPassword123!",
        "role": "rep"
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "admin"


def test_duplicate_registration_rejected(client, admin_user):
    # Duplicate email
    res1 = client.post("/api/v1/auth/register", json={
        "email": admin_user.email,
        "username": "distinct_user",
        "full_name": "Distinct User",
        "password": "Password123!"
    })
    assert res1.status_code == 400
    assert "email" in res1.json()["detail"].lower()

    # Duplicate username
    res2 = client.post("/api/v1/auth/register", json={
        "email": "distinct_email@example.com",
        "username": admin_user.username,
        "full_name": "Distinct User",
        "password": "Password123!"
    })
    assert res2.status_code == 400
    assert "username" in res2.json()["detail"].lower()


def test_login_success_sets_session_cookie(client, admin_user):
    login_payload = {
        "username_or_email": admin_user.username,
        "password": "AdminPass123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == admin_user.email
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # Verify session cookie was set in response headers
    assert settings.COOKIE_NAME in response.cookies
    assert response.cookies[settings.COOKIE_NAME] == data["access_token"]


def test_login_with_email_success(client, admin_user):
    login_payload = {
        "username_or_email": admin_user.email,
        "password": "AdminPass123!"
    }
    response = client.post("/api/v1/auth/login", json=login_payload)
    assert response.status_code == 200
    assert "access_token" in response.json()


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


def test_get_current_user_profile_bearer_header(client, admin_user):
    token = create_access_token(admin_user)
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["id"] == admin_user.id


def test_get_current_user_unauthenticated_failure(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
