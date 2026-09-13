from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User, LeadStatus, LeadPriority
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


NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


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
                return RedirectResponse(
                    url="/dashboard",
                    status_code=status.HTTP_303_SEE_OTHER,
                    headers=NO_CACHE_HEADERS
                )
    return RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
        headers=NO_CACHE_HEADERS
    )


@router.get("/login", response_class=HTMLResponse)
def login_page(
    request: Request,
    next: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Render the server-side HTML login page.
    Redirects already-authenticated users to /dashboard to avoid stale login states upon back-navigation.
    """
    token = get_token_from_request(request)
    if token:
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            auth_service = AuthService(db)
            user = auth_service.get_user_by_id(payload["sub"])
            if user and user.is_active:
                destination = next if (is_safe_url(next) and next != "/login") else "/dashboard"
                return RedirectResponse(
                    url=destination,
                    status_code=status.HTTP_303_SEE_OTHER,
                    headers=NO_CACHE_HEADERS
                )

    safe_next = next if is_safe_url(next) else None
    csrf_token = generate_csrf_token()
    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={
            "csrf_token": csrf_token,
            "next": safe_next,
            "error": None
        },
        headers=NO_CACHE_HEADERS
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
            status_code=status.HTTP_400_BAD_REQUEST,
            headers=NO_CACHE_HEADERS
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers=NO_CACHE_HEADERS
        )

    # 3. Establish Authenticated Session
    token = create_access_token(user)
    destination = safe_next or "/dashboard"

    response = RedirectResponse(
        url=destination,
        status_code=status.HTTP_303_SEE_OTHER,
        headers=NO_CACHE_HEADERS
    )

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
        },
        headers=NO_CACHE_HEADERS
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

    response = RedirectResponse(
        url="/login",
        status_code=status.HTTP_303_SEE_OTHER,
        headers=NO_CACHE_HEADERS
    )
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path=settings.COOKIE_PATH
    )
    return response


@router.get("/leads", response_class=HTMLResponse)
def leads_workspace(
    request: Request,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status: Optional[str] = Query(None),
    industry: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    search: Optional[str] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Render the authenticated Business CRM Leads Workspace.
    Provides lead listing, multi-field partial substring search across name/email/company,
    status/industry/score filtering, field sorting, pagination, and CSV export linkage.
    """
    # Validate and normalize status
    status_enum = None
    if status and status.strip():
        try:
            status_enum = LeadStatus(status.strip())
        except ValueError:
            status_enum = None

    # Validate sort fields
    allowed_sort_fields = {"created_at", "qualification_score", "annual_revenue", "company_size"}
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"

    # Validate sort direction
    if sort_order.lower() not in {"asc", "desc"}:
        sort_order = "desc"
    else:
        sort_order = sort_order.lower()

    # Clean string parameters
    clean_search = search.strip() if search and search.strip() else None
    clean_industry = industry.strip() if industry and industry.strip() else None

    lead_service = LeadService(db)
    result = lead_service.get_leads_paginated(
        page=page,
        size=size,
        status=status_enum,
        industry=clean_industry,
        min_score=min_score,
        search=clean_search,
        sort_by=sort_by,
        sort_order=sort_order
    )

    csrf_token = generate_csrf_token(user_id=current_user.id)
    has_active_filters = bool(clean_search or status_enum or clean_industry or min_score is not None)

    return templates.TemplateResponse(
        request=request,
        name="leads/list.html",
        context={
            "user": current_user,
            "leads_data": result,
            "leads": result["items"],
            "total": result["total"],
            "page": result["page"],
            "size": result["size"],
            "pages": result["pages"],
            "statuses": [s.value for s in LeadStatus],
            "selected_status": status_enum.value if status_enum else "",
            "selected_industry": clean_industry or "",
            "selected_min_score": min_score if min_score is not None else "",
            "search_query": clean_search or "",
            "sort_by": sort_by,
            "sort_order": sort_order,
            "has_active_filters": has_active_filters,
            "csrf_token": csrf_token
        },
        headers=NO_CACHE_HEADERS
    )


@router.get("/leads/export/csv")
def leads_export_csv_web(
    request: Request,
    current_user: User = Depends(get_current_user_web)
):
    """
    Delegate authenticated Web CSV export requests directly to the authoritative REST export endpoint.
    """
    return RedirectResponse(url="/api/v1/leads/export/csv", status_code=status.HTTP_307_TEMPORARY_REDIRECT)

