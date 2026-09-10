from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User, UserRole
from app.schemas import UserCreate, UserResponse, LoginRequest, TokenResponse
from app.services.auth_service import AuthService, create_access_token
from app.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: Session = Depends(get_db)):
    """Register a new user identity."""
    auth_service = AuthService(db)

    if auth_service.get_user_by_email(payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered."
        )

    if auth_service.get_user_by_username(payload.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already taken."
        )

    # Automatically grant ADMIN role to the first registered bootstrap user
    if auth_service.count_users() == 0:
        payload.role = UserRole.ADMIN

    user = auth_service.create_user(payload)
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate credentials, set secure session cookie, and return token."""
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(payload.username_or_email, payload.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = create_access_token(user)

    is_secure = settings.COOKIE_SECURE if settings.COOKIE_SECURE is not None else (settings.ENVIRONMENT.lower() == "production")
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=settings.COOKIE_HTTPONLY,
        secure=is_secure,
        samesite=settings.COOKIE_SAMESITE,
        path=settings.COOKIE_PATH
    )

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=user
    )


@router.post("/logout")
def logout(response: Response):
    """Invalidate authenticated session by clearing the secure HTTP session cookie."""
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path=settings.COOKIE_PATH
    )
    return {"detail": "Successfully logged out."}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Retrieve identity and permissions for the currently authenticated session user."""
    return current_user
