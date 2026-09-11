import hmac
import hashlib
import secrets
import time
from typing import Optional
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.services.auth_service import AuthService, decode_access_token


def is_safe_url(target: Optional[str]) -> bool:
    """
    Validate that a return/redirect URL is a safe internal relative path.
    Prevents open redirects, scheme-relative attacks, and malformed URL vectors.
    """
    if not target or not isinstance(target, str):
        return False
    target = target.strip()
    if not target:
        return False
    if not target.startswith("/") or target.startswith("//") or target.startswith("/\\"):
        return False
    if "\\" in target or "\r" in target or "\n" in target or "\t" in target:
        return False
    path_part = target.split("?")[0].split("#")[0]
    if ":" in path_part:
        return False
    return True


def generate_csrf_token(user_id: Optional[str] = None, expires_in_seconds: Optional[int] = None) -> str:
    """
    Generate an HMAC-SHA256 CSRF token cryptographically bound to SECRET_KEY,
    the user identity (or anonymous), a high-entropy random nonce, and an expiration timestamp.
    """
    if expires_in_seconds is None:
        expires_in_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    exp = int(time.time()) + expires_in_seconds
    subject = user_id if user_id else "anonymous"
    nonce = secrets.token_hex(16)
    payload = f"{subject}:{exp}:{nonce}"
    sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


def validate_csrf_token(token: Optional[str], user_id: Optional[str] = None) -> bool:
    """
    Validate an HMAC-SHA256 CSRF token using constant-time comparison.
    Verifies cryptographic signature, expiration timestamp, and subject binding.
    """
    if not token or not isinstance(token, str):
        return False
    parts = token.split(":")
    if len(parts) != 4:
        return False
    subject, exp_str, nonce, sig = parts
    try:
        exp = int(exp_str)
    except ValueError:
        return False
    if time.time() > exp:
        return False
    expected_subject = user_id if user_id else "anonymous"
    if not secrets.compare_digest(subject, expected_subject):
        return False
    payload = f"{subject}:{exp_str}:{nonce}"
    expected_sig = hmac.new(settings.SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return secrets.compare_digest(sig, expected_sig)


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


def get_current_user_web(request: Request, db: Session = Depends(get_db)) -> User:
    """
    Resolve authenticated user for Web/MVC requests.
    Redirects unauthenticated or invalid sessions to /login.
    """
    target_path = request.url.path
    if request.url.query:
        target_path = f"{target_path}?{request.url.query}"
    redirect_url = f"/login?next={target_path}" if is_safe_url(target_path) and target_path != "/login" else "/login"

    token = get_token_from_request(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": redirect_url}
        )

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": redirect_url}
        )

    auth_service = AuthService(db)
    user = auth_service.get_user_by_id(payload["sub"])
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": redirect_url}
        )

    return user


def require_roles_web(*allowed_roles: UserRole):
    """Factory creating a role authorization dependency for Web routes."""
    def role_checker(current_user: User = Depends(get_current_user_web)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: insufficient role permissions for this Web area."
            )
        return current_user

    return role_checker
