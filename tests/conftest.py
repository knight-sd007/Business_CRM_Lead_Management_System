import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.models import User, UserRole
from app.services.auth_service import hash_password, create_access_token

# Use SQLite in-memory database with StaticPool for complete isolation and memory-only execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(test_db):
    user = User(
        email="admin@test.example.com",
        username="admin_user",
        full_name="Admin Test User",
        role=UserRole.ADMIN,
        password_hash=hash_password("AdminPass123!"),
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def manager_user(test_db):
    user = User(
        email="manager@test.example.com",
        username="manager_user",
        full_name="Manager Test User",
        role=UserRole.MANAGER,
        password_hash=hash_password("ManagerPass123!"),
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def rep_user(test_db):
    user = User(
        email="rep@test.example.com",
        username="rep_user",
        full_name="Sales Rep Test User",
        role=UserRole.REP,
        password_hash=hash_password("RepPass123!"),
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def inactive_user(test_db):
    user = User(
        email="inactive@test.example.com",
        username="inactive_user",
        full_name="Inactive Test User",
        role=UserRole.REP,
        password_hash=hash_password("InactivePass123!"),
        is_active=False
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_client(test_db, admin_user):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        token = create_access_token(admin_user)
        test_client.cookies.set(settings.COOKIE_NAME, token)
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def rep_client(test_db, rep_user):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        token = create_access_token(rep_user)
        test_client.cookies.set(settings.COOKIE_NAME, token)
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def manager_client(test_db, manager_user):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app, raise_server_exceptions=False) as test_client:
        token = create_access_token(manager_user)
        test_client.cookies.set(settings.COOKIE_NAME, token)
        yield test_client
    app.dependency_overrides.clear()
