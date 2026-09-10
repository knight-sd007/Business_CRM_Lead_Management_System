from datetime import datetime, timezone, timedelta
from typing import Optional
import bcrypt
import jwt
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.config import settings
from app.models import User, UserRole
from app.schemas import UserCreate


def hash_password(password: str) -> str:
    """Hash a plaintext password using modern bcrypt with automatic salt generation."""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Securely verify a plaintext password against a stored bcrypt hash."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access/session token for the authenticated user."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role.value if isinstance(user.role, UserRole) else str(user.role),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp())
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access/session token signature and expiration."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


class AuthService:
    def __init__(self, db: Session):
        self.db = db

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    def get_user_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.db.query(User).filter(User.username == username).first()

    def authenticate_user(self, username_or_email: str, password: str) -> Optional[User]:
        user = self.db.query(User).filter(
            or_(User.email == username_or_email, User.username == username_or_email)
        ).first()
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def create_user(self, payload: UserCreate) -> User:
        user_data = payload.model_dump()
        password = user_data.pop("password")
        password_hash = hash_password(password)

        user = User(
            **user_data,
            password_hash=password_hash
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def count_users(self) -> int:
        return self.db.query(User).count()
