from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User
from app.services.auth_service import AuthService, create_access_token, decode_access_token
from app.services.lead_service import LeadService
from app.dependencies import (
    get_current_user_web,
    generate_csrf_token,
    validate_csrf_token,
    is_safe_url,
    get_token_from_request
)

templates = Jinja2Templates(directory="app/templates")

router = APIRouter(include_in_schema=False, default_response_class=HTMLResponse)


@router.get("/", response_class=RedirectResponse)
def root_redirect(request: Request, db: Session = Depends(get_db)):
    """
    Root Web landing route.
    Redirects authenticated users to /dashboard and unauthenticated users to /login.
    """
    token = get_token_from_request(request)
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            auth_service = AuthService(db)
            user = auth_service.get_user_by_id(payload["sub"])
            if user and user.is_active:
                return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Render the server-side HTML login page."""
    safe_next = next if is_safe_url(next) else None
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "csrf_token": csrf_token,
            "next": safe_next,
            "error": None
        }
    )


@router.post("/login")
def login_submit(
    request: Request,
    username_or_email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    next: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Authenticate credentials submitted via the Web login form.
    Validates CSRF token and establishes a secure HTTP-only session cookie upon success.
    """
    safe_next = next if is_safe_url(next) else None

    # 1. CSRF Token Validation
    if not validate_csrf_token(csrf_token):
        new_csrf_token = generate_csrf_token()
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "csrf_token": new_csrf_token,
                "next": safe_next,
                "error": "Invalid or expired security token. Please try again."
            },
            status_code=status.HTTP_400_BAD_REQUEST
        )

    # 2. Authenticate User Credentials
    auth_service = AuthService(db)
    user = auth_service.authenticate_user(username_or_email, password)

    if not user or not user.is_active:
        new_csrf_token = generate_csrf_token()
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={
                "csrf_token": new_csrf_token,
                "next": safe_next,
                "error": "Invalid username/email or password."
            },
            status_code=status.HTTP_401_UNAUTHORIZED
        )

    # 3. Establish Authenticated Session
    token = create_access_token(user)
    destination = safe_next or "/dashboard"

    response = RedirectResponse(url=destination, status_code=status.HTTP_303_SEE_OTHER)

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

    return response


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    request: Request,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Render the authenticated Business CRM web dashboard.
    """
    lead_service = LeadService(db)
    summary = lead_service.get_dashboard_summary()
    csrf_token = generate_csrf_token(user_id=current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "user": current_user,
            "summary": summary,
            "csrf_token": csrf_token
        }
    )


@router.post("/logout")
def logout_submit(
    request: Request,
    csrf_token: str = Form(...),
    current_user: User = Depends(get_current_user_web)
):
    """
    Terminate Web session for the authenticated user after CSRF validation.
    Clears the secure session cookie and redirects to the login screen.
    """
    if not validate_csrf_token(csrf_token, user_id=current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired CSRF token."
        )

    response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path=settings.COOKIE_PATH
    )
    return response
