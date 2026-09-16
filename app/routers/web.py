import urllib.parse
from typing import Optional
from fastapi import APIRouter, Request, Depends, Form, HTTPException, status, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.config import settings
from app.database import get_db
from app.models import User, LeadStatus, LeadPriority
from app.schemas import LeadCreate
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
    status_filter: Optional[str] = Query(None, alias="status"),
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
    if status_filter and status_filter.strip():
        try:
            status_enum = LeadStatus(status_filter.strip())
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

    # Build clean query parameters for pagination links, omitting empty values
    query_params_dict = {}
    if clean_search:
        query_params_dict["search"] = clean_search
    if status_enum:
        query_params_dict["status"] = status_enum.value
    if clean_industry:
        query_params_dict["industry"] = clean_industry
    if min_score is not None:
        query_params_dict["min_score"] = str(min_score)
    if sort_by != "created_at" or "sort_by" in request.query_params:
        if sort_by:
            query_params_dict["sort_by"] = sort_by
    if sort_order != "desc" or "sort_order" in request.query_params:
        if sort_order:
            query_params_dict["sort_order"] = sort_order
    if size != 10 or "size" in request.query_params:
        query_params_dict["size"] = str(size)

    query_string = urllib.parse.urlencode(query_params_dict)
    pagination_query_prefix = f"?{query_string}&" if query_string else "?"

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
            "pagination_query_prefix": pagination_query_prefix,
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


@router.get("/leads/new", response_class=HTMLResponse)
def lead_create_page(
    request: Request,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Render the authenticated Lead Creation form workspace.
    Initializes default values matching the authoritative LeadCreate schema.
    """
    csrf_token = generate_csrf_token(user_id=current_user.id)
    initial_data = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "company_name": "",
        "job_title": "",
        "industry": "Technology",
        "company_size": 10,
        "annual_revenue": 50000.0,
        "assigned_owner": "Unassigned",
        "notes": ""
    }
    return templates.TemplateResponse(
        request=request,
        name="leads/form.html",
        context={
            "user": current_user,
            "csrf_token": csrf_token,
            "form_data": initial_data,
            "errors": {},
            "error": None
        },
        headers=NO_CACHE_HEADERS
    )


@router.post("/leads/new", response_class=HTMLResponse)
async def lead_create_submit(
    request: Request,
    current_user: User = Depends(get_current_user_web),
    db: Session = Depends(get_db)
):
    """
    Handle lead creation form submission.
    Validates CSRF token, normalizes form inputs, validates via Pydantic LeadCreate schema,
    persists through LeadService.create_lead(), and redirects to the Leads Workspace.
    """
    form = await request.form()
    form_data = {k: v for k, v in form.items()}
    csrf_token = form.get("csrf_token", "")

    # 1. CSRF Token Validation
    if not validate_csrf_token(csrf_token, user_id=current_user.id):
        new_csrf_token = generate_csrf_token(user_id=current_user.id)
        return templates.TemplateResponse(
            request=request,
            name="leads/form.html",
            context={
                "user": current_user,
                "csrf_token": new_csrf_token,
                "form_data": form_data,
                "errors": {},
                "error": "Invalid or expired security token. Please try again."
            },
            status_code=status.HTTP_400_BAD_REQUEST,
            headers=NO_CACHE_HEADERS
        )

    # 2. Minimal Normalization for Web Form Input
    first_name_raw = form.get("first_name", "")
    last_name_raw = form.get("last_name", "")
    email_raw = form.get("email", "")
    company_name_raw = form.get("company_name", "")
    phone_raw = form.get("phone", "")
    job_title_raw = form.get("job_title", "")
    industry_raw = form.get("industry", "")
    company_size_raw = form.get("company_size", "")
    annual_revenue_raw = form.get("annual_revenue", "")
    assigned_owner_raw = form.get("assigned_owner", "")
    notes_raw = form.get("notes", "")

    first_name = first_name_raw.strip() if isinstance(first_name_raw, str) else ""
    last_name = last_name_raw.strip() if isinstance(last_name_raw, str) else ""
    email = email_raw.strip() if isinstance(email_raw, str) else ""
    company_name = company_name_raw.strip() if isinstance(company_name_raw, str) else ""

    phone = phone_raw.strip() if (isinstance(phone_raw, str) and phone_raw.strip()) else None
    job_title = job_title_raw.strip() if (isinstance(job_title_raw, str) and job_title_raw.strip()) else None
    industry = industry_raw.strip() if (isinstance(industry_raw, str) and industry_raw.strip()) else "Technology"
    assigned_owner = assigned_owner_raw.strip() if (isinstance(assigned_owner_raw, str) and assigned_owner_raw.strip()) else "Unassigned"
    notes = notes_raw.strip() if (isinstance(notes_raw, str) and notes_raw.strip()) else None

    errors: dict[str, str] = {}

    # Parse numeric fields with fallback to schema defaults on empty input
    company_size_val = None
    if isinstance(company_size_raw, str) and not company_size_raw.strip():
        company_size_val = 10
    else:
        try:
            company_size_val = int(company_size_raw)
        except (ValueError, TypeError):
            errors["company_size"] = "Company size must be a valid integer."

    annual_revenue_val = None
    if isinstance(annual_revenue_raw, str) and not annual_revenue_raw.strip():
        annual_revenue_val = 50000.0
    else:
        try:
            annual_revenue_val = float(annual_revenue_raw)
        except (ValueError, TypeError):
            errors["annual_revenue"] = "Annual revenue must be a valid number."

    lead_create: Optional[LeadCreate] = None
    if not errors:
        payload_dict = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": phone,
            "company_name": company_name,
            "job_title": job_title,
            "industry": industry,
            "company_size": company_size_val,
            "annual_revenue": annual_revenue_val,
            "assigned_owner": assigned_owner,
            "notes": notes,
        }

        try:
            lead_create = LeadCreate(**payload_dict)
        except ValidationError as exc:
            for err in exc.errors():
                loc = err.get("loc", [])
                field_name = str(loc[0]) if loc else "general"
                msg = err.get("msg", "Invalid value.")
                if msg.startswith("Value error, "):
                    msg = msg[13:]
                if field_name not in errors:
                    errors[field_name] = msg

    if errors or lead_create is None:
        new_csrf_token = generate_csrf_token(user_id=current_user.id)
        return templates.TemplateResponse(
            request=request,
            name="leads/form.html",
            context={
                "user": current_user,
                "csrf_token": new_csrf_token,
                "form_data": form_data,
                "errors": errors,
                "error": "Please correct the highlighted errors before proceeding."
            },
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            headers=NO_CACHE_HEADERS
        )

    # 4. Authoritative Service Execution
    lead_service = LeadService(db)
    lead_service.create_lead(lead_create)

    # 5. Success Redirect to Leads Workspace
    return RedirectResponse(
        url="/leads",
        status_code=status.HTTP_303_SEE_OTHER,
        headers=NO_CACHE_HEADERS
    )
