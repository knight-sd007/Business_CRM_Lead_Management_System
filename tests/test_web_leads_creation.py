import re
import pytest
from app.models import Lead, ActivityLog, LeadStatus, LeadPriority, ActivityType
from app.dependencies import generate_csrf_token, validate_csrf_token


def extract_csrf_token(html_text: str) -> str:
    """Helper to extract csrf_token value from rendered HTML form."""
    match = re.search(r'name=["\']csrf_token["\']\s+value=["\']([^"\']+)["\']', html_text)
    if not match:
        match = re.search(r'value=["\']([^"\']+)["\']\s+name=["\']csrf_token["\']', html_text)
    assert match is not None, "CSRF token not found in HTML response"
    return match.group(1)


def test_tc_lead_create_01_unauthenticated_get_redirects_to_login(client):
    """TC-LEAD-CREATE-01: Unauthenticated GET /leads/new -> 303 Redirect to /login?next=/leads/new."""
    response = client.get("/leads/new", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login?next=/leads/new"


def test_tc_lead_create_02_unauthenticated_post_redirects_to_login(client):
    """TC-LEAD-CREATE-02: Unauthenticated POST /leads/new -> 303 Redirect to /login?next=/leads/new."""
    response = client.post(
        "/leads/new",
        data={
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah@example.com",
            "company_name": "Cyberdyne",
            "csrf_token": "some-token"
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/login?next=/leads/new"


def test_tc_lead_create_03_authenticated_admin_get_form(auth_client, admin_user):
    """TC-LEAD-CREATE-03: Authenticated Admin can access GET /leads/new and see the creation form."""
    response = auth_client.get("/leads/new")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Create New Lead" in response.text
    assert "Contact Information" in response.text
    assert "Company &amp; Industry Profile" in response.text or "Company & Industry Profile" in response.text
    assert "Ownership &amp; Notes" in response.text or "Ownership & Notes" in response.text
    assert admin_user.full_name in response.text
    assert "Admin" in response.text


def test_tc_lead_create_04_authenticated_manager_get_form(manager_client, manager_user):
    """TC-LEAD-CREATE-04: Authenticated Manager can access GET /leads/new."""
    response = manager_client.get("/leads/new")
    assert response.status_code == 200
    assert "Create New Lead" in response.text
    assert manager_user.full_name in response.text
    assert "Manager" in response.text


def test_tc_lead_create_05_authenticated_rep_get_form(rep_client, rep_user):
    """TC-LEAD-CREATE-05: Authenticated Sales Rep can access GET /leads/new."""
    response = rep_client.get("/leads/new")
    assert response.status_code == 200
    assert "Create New Lead" in response.text
    assert rep_user.full_name in response.text
    assert "Sales Rep" in response.text


def test_tc_lead_create_06_csrf_token_present_and_valid(auth_client, admin_user):
    """TC-LEAD-CREATE-06: GET /leads/new embeds a valid HMAC-SHA256 CSRF token."""
    response = auth_client.get("/leads/new")
    assert response.status_code == 200
    token = extract_csrf_token(response.text)
    assert validate_csrf_token(token, user_id=admin_user.id) is True


def test_tc_lead_create_07_qualification_score_and_priority_inputs_absent(auth_client):
    """TC-LEAD-CREATE-07: Form MUST NOT contain inputs for server-controlled score and priority."""
    response = auth_client.get("/leads/new")
    assert response.status_code == 200
    html = response.text
    assert 'name="qualification_score"' not in html
    assert 'name="priority"' not in html


def test_tc_lead_create_08_status_input_absent(auth_client):
    """TC-LEAD-CREATE-08: Form MUST NOT contain an input for status (defaults to LeadStatus.NEW)."""
    response = auth_client.get("/leads/new")
    assert response.status_code == 200
    html = response.text
    assert 'name="status"' not in html


def test_tc_lead_create_09_empty_required_form_returns_422(auth_client, admin_user):
    """TC-LEAD-CREATE-09: Submitting form with missing required fields returns 422 with field-level errors."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "",
            "last_name": "",
            "email": "",
            "company_name": ""
        }
    )
    assert response.status_code == 422
    assert "text/html" in response.headers.get("content-type", "")
    assert "error-first_name" in response.text
    assert "error-last_name" in response.text
    assert "error-email" in response.text
    assert "error-company_name" in response.text
    assert 'aria-invalid="true"' in response.text


def test_tc_lead_create_10_invalid_email_returns_422_with_preserved_input(auth_client, admin_user):
    """TC-LEAD-CREATE-10: Invalid email address returns 422 and preserves entered form fields."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Eleanor",
            "last_name": "Vance",
            "email": "not-an-email",
            "company_name": "HillCorp Enterprises",
            "job_title": "VP Operations",
            "notes": "Interested in enterprise tier."
        }
    )
    assert response.status_code == 422
    assert "error-email" in response.text
    # Preserved values check
    assert 'value="Eleanor"' in response.text
    assert 'value="Vance"' in response.text
    assert 'value="not-an-email"' in response.text
    assert 'value="HillCorp Enterprises"' in response.text
    assert 'value="VP Operations"' in response.text
    assert "Interested in enterprise tier." in response.text


def test_tc_lead_create_11_negative_company_size_returns_422(auth_client, admin_user):
    """TC-LEAD-CREATE-11: Company size < 1 returns 422 with validation error."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah@cyberdyne.example.com",
            "company_name": "Cyberdyne Systems",
            "company_size": "-5"
        }
    )
    assert response.status_code == 422
    assert "error-company_size" in response.text
    assert 'value="-5"' in response.text


def test_tc_lead_create_12_negative_annual_revenue_returns_422(auth_client, admin_user):
    """TC-LEAD-CREATE-12: Negative annual revenue returns 422 with validation error."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah@cyberdyne.example.com",
            "company_name": "Cyberdyne Systems",
            "annual_revenue": "-1000.0"
        }
    )
    assert response.status_code == 422
    assert "error-annual_revenue" in response.text
    assert 'value="-1000.0"' in response.text


def test_tc_lead_create_13_invalid_csrf_returns_400(auth_client):
    """TC-LEAD-CREATE-13: Invalid CSRF token returns 400 Bad Request with error notification."""
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": "tampered-or-expired-token-12345",
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah@cyberdyne.example.com",
            "company_name": "Cyberdyne Systems"
        }
    )
    assert response.status_code == 400
    assert "Invalid or expired security token" in response.text


def test_tc_lead_create_14_xss_first_name_safely_escaped(auth_client, admin_user):
    """TC-LEAD-CREATE-14: XSS payload in first_name is safely HTML-escaped upon validation error re-render."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    payload_xss = "<script>alert('xss')</script>"
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": payload_xss,
            "last_name": "Tester",
            "email": "invalid-email-to-trigger-rerender",
            "company_name": "Security Labs"
        }
    )
    assert response.status_code == 422
    raw_html = response.text
    assert "<script>alert('xss')</script>" not in raw_html
    assert "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in raw_html or "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;" in raw_html or "&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;" in raw_html or "alert(&#39;xss&#39;)" in raw_html


def test_tc_lead_create_15_xss_notes_safely_escaped(auth_client, admin_user):
    """TC-LEAD-CREATE-15: XSS payload in notes textarea is safely HTML-escaped upon validation error re-render."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    payload_xss = "<img src=x onerror=alert(1)>"
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "ValidFirst",
            "last_name": "ValidLast",
            "email": "invalid-email",
            "company_name": "Valid Company",
            "notes": payload_xss
        }
    )
    assert response.status_code == 422
    raw_html = response.text
    assert "<img src=x onerror=alert(1)>" not in raw_html
    assert "&lt;img src=x onerror=alert(1)&gt;" in raw_html or "&lt;img src=x onerror=alert(1)&gt;" in raw_html


def test_tc_lead_create_16_valid_minimum_lead_creates_and_redirects(auth_client, admin_user, test_db):
    """TC-LEAD-CREATE-16: Valid lead with minimum required fields creates record and redirects 303 to /leads."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Alice",
            "last_name": "Smith",
            "email": "alice.smith@alpha.example.com",
            "company_name": "Alpha Dynamics"
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/leads"

    # Verify DB persistence
    lead = test_db.query(Lead).filter(Lead.email == "alice.smith@alpha.example.com").first()
    assert lead is not None
    assert lead.first_name == "Alice"
    assert lead.last_name == "Smith"
    assert lead.company_name == "Alpha Dynamics"
    assert lead.status == LeadStatus.NEW
    assert lead.industry == "Technology"  # Schema default
    assert lead.company_size == 10        # Schema default
    assert lead.annual_revenue == 50000.0 # Schema default
    assert lead.assigned_owner == "Unassigned"  # Schema default
    assert lead.qualification_score > 0
    assert lead.priority in [LeadPriority.LOW, LeadPriority.MEDIUM, LeadPriority.HIGH, LeadPriority.URGENT]


def test_tc_lead_create_17_valid_high_value_lead_generates_scoring(auth_client, admin_user, test_db):
    """TC-LEAD-CREATE-17: High revenue and C-level title generates qualification score 100 and Urgent priority."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Sarah",
            "last_name": "Connor",
            "email": "sarah.connor@cyberdyne.example.com",
            "company_name": "Cyberdyne Systems",
            "job_title": "Chief Technology Officer",
            "industry": "Technology",
            "company_size": "600",
            "annual_revenue": "1500000.0",
            "assigned_owner": "Alex Rivera",
            "notes": "Strategic opportunity."
        },
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers.get("location") == "/leads"

    lead = test_db.query(Lead).filter(Lead.email == "sarah.connor@cyberdyne.example.com").first()
    assert lead is not None
    assert lead.qualification_score == 100
    assert lead.priority == LeadPriority.URGENT
    assert lead.status == LeadStatus.NEW
    assert lead.assigned_owner == "Alex Rivera"


def test_tc_lead_create_18_initial_activity_log_created_by_service(auth_client, admin_user, test_db):
    """TC-LEAD-CREATE-18: LeadService.create_lead automatically logs initial ActivityLog."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Marcus",
            "last_name": "Vance",
            "email": "marcus.vance@apexcloud.example.com",
            "company_name": "Apex Cloud Dynamics",
            "assigned_owner": "Alex Rivera"
        },
        follow_redirects=False
    )
    assert response.status_code == 303

    lead = test_db.query(Lead).filter(Lead.email == "marcus.vance@apexcloud.example.com").first()
    assert lead is not None
    activities = test_db.query(ActivityLog).filter(ActivityLog.lead_id == lead.id).all()
    assert len(activities) == 1
    assert activities[0].activity_type == ActivityType.NOTE
    assert "Lead created with qualification score" in activities[0].description
    assert activities[0].performed_by == "Alex Rivera"


def test_tc_lead_create_19_create_lead_link_exists_on_leads_workspace(auth_client):
    """TC-LEAD-CREATE-19: Leads Workspace (/leads) contains 'Create Lead' button linking to /leads/new."""
    response = auth_client.get("/leads")
    assert response.status_code == 200
    assert 'href="/leads/new"' in response.text
    assert "Create Lead" in response.text


def test_tc_lead_create_20_validation_errors_preserve_all_form_values(auth_client, admin_user):
    """TC-LEAD-CREATE-20: Form values across all sections are preserved when validation error occurs."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "John",
            "last_name": "Doe",
            "email": "invalid-email-format",
            "phone": "+1-555-0199",
            "company_name": "Acme Global",
            "job_title": "Director of Engineering",
            "industry": "Finance",
            "company_size": "250",
            "annual_revenue": "850000.0",
            "assigned_owner": "Jane Smith",
            "notes": "Met at industry summit in Chicago."
        }
    )
    assert response.status_code == 422
    html = response.text
    assert 'value="John"' in html
    assert 'value="Doe"' in html
    assert 'value="invalid-email-format"' in html
    assert 'value="+1-555-0199"' in html
    assert 'value="Acme Global"' in html
    assert 'value="Director of Engineering"' in html
    assert 'value="Finance"' in html
    assert 'value="250"' in html
    assert 'value="850000.0"' in html
    assert 'value="Jane Smith"' in html
    assert "Met at industry summit in Chicago." in html


def test_tc_lead_create_21_optional_blank_fields_use_authoritative_defaults(auth_client, admin_user, test_db):
    """TC-LEAD-CREATE-21: Blank optional strings and numbers default to schema values."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Default",
            "last_name": "User",
            "email": "default.user@example.com",
            "company_name": "Default Corp",
            "phone": "   ",
            "job_title": "",
            "industry": "",
            "company_size": "",
            "annual_revenue": "",
            "assigned_owner": "",
            "notes": "   "
        },
        follow_redirects=False
    )
    assert response.status_code == 303

    lead = test_db.query(Lead).filter(Lead.email == "default.user@example.com").first()
    assert lead is not None
    assert lead.phone is None
    assert lead.job_title is None
    assert lead.industry == "Technology"
    assert lead.company_size == 10
    assert lead.annual_revenue == 50000.0
    assert lead.assigned_owner == "Unassigned"
    assert lead.notes is None


def test_tc_lead_create_22_malformed_numeric_values_return_validation_errors(auth_client, admin_user):
    """TC-LEAD-CREATE-22: Non-numeric strings in company_size and annual_revenue return 422."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": "Numeric",
            "last_name": "Test",
            "email": "numeric@example.com",
            "company_name": "Numeric Co",
            "company_size": "abc",
            "annual_revenue": "xyz"
        }
    )
    assert response.status_code == 422
    assert "error-company_size" in response.text
    assert "error-annual_revenue" in response.text


def test_tc_lead_create_23_oversized_strings_return_validation_errors(auth_client, admin_user):
    """TC-LEAD-CREATE-23: Oversized string fields exceed max_length and return 422."""
    csrf_token = generate_csrf_token(user_id=admin_user.id)
    oversized_name = "A" * 150  # max 100
    response = auth_client.post(
        "/leads/new",
        data={
            "csrf_token": csrf_token,
            "first_name": oversized_name,
            "last_name": "ValidLast",
            "email": "valid@example.com",
            "company_name": "Valid Co"
        }
    )
    assert response.status_code == 422
    assert "error-first_name" in response.text


def test_tc_lead_create_24_double_submit_protection_compatible_with_crm_js(auth_client, client):
    """TC-LEAD-CREATE-24: Form rendered on /leads/new integrates with crm.js double-submit protection."""
    # 1. Form rendered on /leads/new is a standard POST form
    response = auth_client.get("/leads/new")
    assert response.status_code == 200
    assert 'class="lead-form"' in response.text
    assert 'method="POST"' in response.text
    assert 'action="/leads/new"' in response.text
    assert 'id="lead-create-form"' in response.text

    # 2. Verify crm.js attaches to forms excluding only filter forms
    res_js = client.get("/static/js/crm.js")
    assert res_js.status_code == 200
    assert "form:not(.leads-filter-form)" in res_js.text
    assert "data-submitting" in res_js.text or "dataset.submitting" in res_js.text
