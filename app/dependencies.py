from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.services.auth_service import AuthService, decode_access_token


def get_token_from_request(request: Request) -> Optional[str]:
    """
    Extract access/session token from HTTP-only cookie first, 
    falling back to Authorization Bearer header.
    """
    # Check session cookie (primary mechanism for browser/MVC and API)
    token = request.cookies.get(settings.COOKIE_NAME)
    if token:
        return token

    # Check Authorization header (standard REST fallback)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Resolve the currently authenticated and active user from session token."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user


def require_roles(*allowed_roles: UserRole):
    """Factory creating an authorization dependency enforcing specific user roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: insufficient role permissions for this operation."
            )
        return current_user

    return role_checker
