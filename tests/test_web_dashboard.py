import pytest
import re
from app.models import Lead, LeadStatus, LeadPriority
from app.dependencies import validate_csrf_token


def extract_csrf_token(html_text: str) -> str:
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text)
    if not match:
        match = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', html_text)
    assert match is not None, "CSRF token not found in HTML response"
    return match.group(1)


def test_tc_dash_01_unauthenticated_root_redirects_to_login(client):
    """TC-DASH-01: Unauthenticated GET / -> 303 -> /login."""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login"


def test_tc_dash_02_authenticated_root_redirects_to_dashboard(auth_client):
    """TC-DASH-02: Authenticated GET / -> 303 -> /dashboard."""
    response = auth_client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/dashboard"


def test_tc_dash_03_unauthenticated_dashboard_redirects_to_login(client):
    """TC-DASH-03: Unauthenticated GET /dashboard -> 303 -> /login?next=/dashboard."""
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login?next=/dashboard"


def test_tc_dash_04_authenticated_dashboard_admin(auth_client, admin_user):
    """TC-DASH-04: Authenticated GET /dashboard as ADMIN -> 200 HTML, user identity & role visible."""
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "CRM Executive Dashboard" in response.text
    assert admin_user.full_name in response.text
    assert "Admin" in response.text


def test_tc_dash_05_authenticated_dashboard_manager(manager_client, manager_user):
    """TC-DASH-05: Authenticated GET /dashboard as MANAGER -> 200 HTML."""
    response = manager_client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "CRM Executive Dashboard" in response.text
    assert manager_user.full_name in response.text
    assert "Manager" in response.text


def test_tc_dash_06_authenticated_dashboard_rep(rep_client, rep_user):
    """TC-DASH-06: Authenticated GET /dashboard as REP -> 200 HTML, no artificial ownership filtering."""
    response = rep_client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "CRM Executive Dashboard" in response.text
    assert rep_user.full_name in response.text
    assert "Sales Rep" in response.text


def test_tc_dash_07_login_success_without_next_redirects_to_dashboard(client, admin_user):
    """TC-DASH-07: Successful login without next -> 303 -> /dashboard, crm_session established."""
    get_res = client.get("/login")
    csrf_token = extract_csrf_token(get_res.text)

    post_res = client.post(
        "/login",
        data={
            "username_or_email": admin_user.username,
            "password": "AdminPass123!",
            "csrf_token": csrf_token
        },
        follow_redirects=False
    )
    assert post_res.status_code == 303
    assert post_res.headers.get("location") == "/dashboard"
    assert "crm_session" in post_res.cookies


def test_tc_dash_08_login_success_with_safe_next(client, admin_user):
    """TC-DASH-08: Successful login with safe next=/dashboard -> 303 -> /dashboard."""
    get_res = client.get("/login?next=/dashboard")
    csrf_token = extract_csrf_token(get_res.text)

    post_res = client.post(
        "/login",
        data={
            "username_or_email": admin_user.username,
            "password": "AdminPass123!",
            "csrf_token": csrf_token,
            "next": "/dashboard"
        },
        follow_redirects=False
    )
    assert post_res.status_code == 303
    assert post_res.headers.get("location") == "/dashboard"


def test_tc_dash_09_login_success_with_malicious_next_falls_back_to_dashboard(client, admin_user):
    """TC-DASH-09: Successful login with malicious next=//evil.example -> 303 -> /dashboard."""
    get_res = client.get("/login?next=//evil.example")
    csrf_token = extract_csrf_token(get_res.text)

    post_res = client.post(
        "/login",
        data={
            "username_or_email": admin_user.username,
            "password": "AdminPass123!",
            "csrf_token": csrf_token,
            "next": "//evil.example"
        },
        follow_redirects=False
    )
    assert post_res.status_code == 303
    assert post_res.headers.get("location") == "/dashboard"


def test_tc_dash_10_seeded_lead_data_metrics(auth_client, test_db):
    """TC-DASH-10: Seeded lead data correctly renders in dashboard metrics."""
    lead1 = Lead(
        first_name="Alice",
        last_name="Walker",
        email="alice@techcorp.example.com",
        company_name="TechCorp Dynamics",
        job_title="CTO",
        industry="Technology",
        company_size=200,
        annual_revenue=1500000.0,
        status=LeadStatus.QUALIFIED,
        priority=LeadPriority.URGENT,
        qualification_score=95,
        assigned_owner="Alex Rivera"
    )
    lead2 = Lead(
        first_name="Bob",
        last_name="Stone",
        email="bob@retailbiz.example.com",
        company_name="RetailBiz Solutions",
        job_title="Sales Manager",
        industry="Retail",
        company_size=15,
        annual_revenue=50000.0,
        status=LeadStatus.UNQUALIFIED,
        priority=LeadPriority.LOW,
        qualification_score=35,
        assigned_owner="Unassigned"
    )
    lead3 = Lead(
        first_name="Charlie",
        last_name="Dunn",
        email="charlie@financehub.example.com",
        company_name="FinanceHub Inc",
        job_title="Director",
        industry="Finance",
        company_size=80,
        annual_revenue=300000.0,
        status=LeadStatus.NEW,
        priority=LeadPriority.HIGH,
        qualification_score=70,
        assigned_owner="Alex Rivera"
    )
    test_db.add_all([lead1, lead2, lead3])
    test_db.commit()

    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    html = response.text

    # Total leads = 3
    assert "Total Leads" in html
    assert '<div class="kpi-value" id="kpi-total-leads">3</div>' in html

    # Qualified = 1, Unqualified = 1
    assert '<div class="kpi-value" id="kpi-qualified-leads">1</div>' in html
    assert '<div class="kpi-value" id="kpi-unqualified-leads">1</div>' in html

    # Pipeline Value = 1,500,000 + 50,000 + 300,000 = 1,850,000.00
    assert "$1,850,000.00" in html

    # Average score = (95 + 35 + 70) / 3 = 66.7
    assert "66.7" in html

    # Status distribution check
    assert "Pipeline Status Distribution" in html

    # Priority distribution check
    assert "Priority Classification" in html

    # Recent leads check
    assert "TechCorp Dynamics" in html
    assert "RetailBiz Solutions" in html
    assert "FinanceHub Inc" in html


def test_tc_dash_11_empty_database_metrics(auth_client):
    """TC-DASH-11: Empty database renders 200 with zero metrics and empty state."""
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    html = response.text

    assert '<div class="kpi-value" id="kpi-total-leads">0</div>' in html
    assert '<div class="kpi-value" id="kpi-qualified-leads">0</div>' in html
    assert '<div class="kpi-value" id="kpi-unqualified-leads">0</div>' in html
    assert "$0.00" in html
    assert "0.0" in html
    assert "No leads found in the system." in html


def test_tc_dash_12_authenticated_dashboard_logout_csrf(auth_client, admin_user):
    """TC-DASH-12: Logout form contains CSRF field without exposing token visibly in dashboard body."""
    response = auth_client.get("/dashboard")
    assert response.status_code == 200
    html = response.text

    csrf_token = extract_csrf_token(html)
    assert validate_csrf_token(csrf_token, user_id=admin_user.id) is True
    # Verify token is in a hidden input and not plainly printed as text
    assert f'<input type="hidden" name="csrf_token" value="{csrf_token}">' in html


def test_tc_dash_13_openapi_schema_isolation(client):
    """TC-DASH-13: /dashboard is absent from /openapi.json, and REST routes remain documented."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    paths = schema.get("paths", {})

    # Web UI routes MUST be absent
    assert "/" not in paths
    assert "/login" not in paths
    assert "/logout" not in paths
    assert "/dashboard" not in paths

    # Programmatic REST endpoints MUST remain
    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/leads" in paths
    assert "/api/v1/leads/{lead_id}" in paths
    assert "/health" in paths
