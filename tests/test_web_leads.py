import pytest
import html
from app.models import Lead, LeadStatus, LeadPriority


def test_tc_leads_01_unauthenticated_leads_redirects_to_login(client):
    """TC-LEADS-01: Unauthenticated GET /leads -> 303 Redirect to /login?next=/leads."""
    response = client.get("/leads", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers.get("location") == "/login?next=/leads"


def test_tc_leads_02_authenticated_admin_access_leads_workspace(auth_client, admin_user):
    """TC-LEADS-02: Authenticated ADMIN can access /leads workspace and sees UI header."""
    response = auth_client.get("/leads")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "Leads Workspace" in response.text
    assert admin_user.full_name in response.text
    assert "Admin" in response.text


def test_tc_leads_03_authenticated_manager_access_leads_workspace(manager_client, manager_user):
    """TC-LEADS-03: Authenticated MANAGER can access /leads workspace."""
    response = manager_client.get("/leads")
    assert response.status_code == 200
    assert "Leads Workspace" in response.text
    assert manager_user.full_name in response.text
    assert "Manager" in response.text


def test_tc_leads_04_authenticated_rep_access_leads_workspace(rep_client, rep_user):
    """TC-LEADS-04: Authenticated SALES REP can access /leads workspace."""
    response = rep_client.get("/leads")
    assert response.status_code == 200
    assert "Leads Workspace" in response.text
    assert rep_user.full_name in response.text
    assert "Sales Rep" in response.text


def test_tc_leads_05_empty_database_state(auth_client):
    """TC-LEADS-05: Empty database renders dedicated empty pipeline state."""
    response = auth_client.get("/leads")
    assert response.status_code == 200
    assert "No leads in pipeline" in response.text
    assert "0 Leads" in response.text


def test_tc_leads_06_populated_lead_list(auth_client, test_db):
    """TC-LEADS-06: Seeded leads render correctly in table rows with badges and pills."""
    lead = Lead(
        first_name="Eleanor",
        last_name="Vance",
        email="eleanor.vance@hillcorp.example.com",
        company_name="HillCorp Enterprises",
        job_title="VP Operations",
        industry="Technology",
        company_size=120,
        annual_revenue=850000.0,
        status=LeadStatus.QUALIFIED,
        priority=LeadPriority.URGENT,
        qualification_score=85,
        assigned_owner="Alex Rivera"
    )
    test_db.add(lead)
    test_db.commit()

    response = auth_client.get("/leads")
    assert response.status_code == 200
    content = response.text

    assert "HillCorp Enterprises" in content
    assert "Eleanor Vance" in content
    assert "eleanor.vance@hillcorp.example.com" in content
    assert "VP Operations" in content
    assert "Technology" in content
    assert "Qualified" in content
    assert "Urgent" in content
    assert "85" in content
    assert "Alex Rivera" in content
    assert "1 Lead" in content


def test_tc_leads_07_search_filtering(auth_client, test_db):
    """TC-LEADS-07: Search parameter filters across first_name, last_name, email, company_name."""
    lead1 = Lead(
        first_name="Alice",
        last_name="Smith",
        email="asmith@alpha.example.com",
        company_name="Alpha Dynamics",
        status=LeadStatus.NEW
    )
    lead2 = Lead(
        first_name="Bob",
        last_name="Jones",
        email="bjones@beta.example.com",
        company_name="Beta Logistics",
        status=LeadStatus.CONTACTED
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    # Search by company name
    res_company = auth_client.get("/leads?search=Alpha")
    assert res_company.status_code == 200
    assert "Alpha Dynamics" in res_company.text
    assert "Beta Logistics" not in res_company.text

    # Search by email
    res_email = auth_client.get("/leads?search=bjones@beta")
    assert res_email.status_code == 200
    assert "Beta Logistics" in res_email.text
    assert "Alpha Dynamics" not in res_email.text


def test_tc_leads_08_status_filtering(auth_client, test_db):
    """TC-LEADS-08: Status parameter filters leads by exact LeadStatus."""
    lead1 = Lead(
        first_name="Charlie",
        last_name="Brown",
        email="cbrown@peanuts.example.com",
        company_name="Peanuts Co",
        status=LeadStatus.QUALIFIED
    )
    lead2 = Lead(
        first_name="Lucy",
        last_name="Van Pelt",
        email="lucy@psych.example.com",
        company_name="Psych Clinic",
        status=LeadStatus.UNQUALIFIED
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    res_qual = auth_client.get("/leads?status=Qualified")
    assert res_qual.status_code == 200
    assert "Peanuts Co" in res_qual.text
    assert "Psych Clinic" not in res_qual.text


def test_tc_leads_09_industry_filtering(auth_client, test_db):
    """TC-LEADS-09: Industry parameter filters leads by case-insensitive partial match."""
    lead1 = Lead(
        first_name="Fin",
        last_name="User",
        email="fin@fintech.example.com",
        company_name="FinTech Corp",
        industry="Finance"
    )
    lead2 = Lead(
        first_name="Health",
        last_name="User",
        email="health@med.example.com",
        company_name="MedLife Labs",
        industry="Healthcare"
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    res_ind = auth_client.get("/leads?industry=Finance")
    assert res_ind.status_code == 200
    assert "FinTech Corp" in res_ind.text
    assert "MedLife Labs" not in res_ind.text


def test_tc_leads_10_min_score_filtering(auth_client, test_db):
    """TC-LEADS-10: Min score parameter filters leads with qualification_score >= min_score."""
    lead1 = Lead(
        first_name="High",
        last_name="Score",
        email="high@example.com",
        company_name="High Score Corp",
        qualification_score=90
    )
    lead2 = Lead(
        first_name="Low",
        last_name="Score",
        email="low@example.com",
        company_name="Low Score Corp",
        qualification_score=30
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    res_score = auth_client.get("/leads?min_score=75")
    assert res_score.status_code == 200
    assert "High Score Corp" in res_score.text
    assert "Low Score Corp" not in res_score.text


def test_tc_leads_11_sorting_fields_and_order(auth_client, test_db):
    """TC-LEADS-11: sort_by and sort_order parameters correctly order leads."""
    lead1 = Lead(
        first_name="Alpha",
        last_name="Corp",
        email="alpha@example.com",
        company_name="Alpha Small",
        annual_revenue=10000.0,
        company_size=5
    )
    lead2 = Lead(
        first_name="Omega",
        last_name="Corp",
        email="omega@example.com",
        company_name="Omega Huge",
        annual_revenue=1000000.0,
        company_size=500
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    res_desc = auth_client.get("/leads?sort_by=annual_revenue&sort_order=desc")
    assert res_desc.status_code == 200
    omega_pos = res_desc.text.find("Omega Huge")
    alpha_pos = res_desc.text.find("Alpha Small")
    assert omega_pos < alpha_pos

    res_asc = auth_client.get("/leads?sort_by=annual_revenue&sort_order=asc")
    assert res_asc.status_code == 200
    alpha_pos_asc = res_asc.text.find("Alpha Small")
    omega_pos_asc = res_asc.text.find("Omega Huge")
    assert alpha_pos_asc < omega_pos_asc


def test_tc_leads_12_pagination_and_query_preservation(auth_client, test_db):
    """TC-LEADS-12: Pagination splits records across pages and preserves filter state in nav links."""
    leads = [
        Lead(
            first_name=f"Lead{i:02d}",
            last_name="Test",
            email=f"lead{i:02d}@example.com",
            company_name=f"Company {i:02d}",
            industry="Technology"
        )
        for i in range(15)
    ]
    test_db.add_all(leads)
    test_db.commit()

    # Page 1 (size=10)
    res_p1 = auth_client.get("/leads?page=1&size=10&industry=Technology")
    assert res_p1.status_code == 200
    assert "Showing <strong>1</strong> to <strong>10</strong> of <strong>15</strong> leads" in res_p1.text
    assert "page=2" in res_p1.text
    assert "industry=Technology" in res_p1.text

    # Page 2 (size=10)
    res_p2 = auth_client.get("/leads?page=2&size=10&industry=Technology")
    assert res_p2.status_code == 200
    assert "Showing <strong>11</strong> to <strong>15</strong> of <strong>15</strong> leads" in res_p2.text


def test_tc_leads_13_no_matching_filtered_results_state(auth_client, test_db):
    """TC-LEADS-13: Filter query returning zero matches displays 'No matching leads found' with reset option."""
    lead = Lead(
        first_name="Exist",
        last_name="Lead",
        email="exist@example.com",
        company_name="Existing Co"
    )
    test_db.add(lead)
    test_db.commit()

    res = auth_client.get("/leads?search=NonExistentKeywordXYZ")
    assert res.status_code == 200
    assert "No matching leads found" in res.text
    assert "Clear All Filters" in res.text or "Reset Filters" in res.text


def test_tc_leads_14_csv_export_link_and_route(auth_client, test_db):
    """TC-LEADS-14: CSV export button links to authoritative backend and /leads/export/csv delegates."""
    lead = Lead(
        first_name="Export",
        last_name="Person",
        email="export@company.example.com",
        company_name="Export Test Co",
        annual_revenue=250000.0,
        qualification_score=80,
        status=LeadStatus.QUALIFIED
    )
    test_db.add(lead)
    test_db.commit()

    # Direct Web delegation route
    res_web = auth_client.get("/leads/export/csv", follow_redirects=False)
    assert res_web.status_code in [302, 307]
    assert res_web.headers.get("location") == "/api/v1/leads/export/csv"

    # Following export to API endpoint
    res_api = auth_client.get("/api/v1/leads/export/csv")
    assert res_api.status_code == 200
    assert "text/csv" in res_api.headers.get("content-type", "")
    assert "Export Test Co" in res_api.text
    assert "export@company.example.com" in res_api.text


def test_tc_leads_15_html_escaping_resilience(auth_client, test_db):
    """TC-LEADS-15: Lead data with HTML characters is safely escaped to prevent XSS injection."""
    lead = Lead(
        first_name="<script>alert(1)</script>",
        last_name="<b>XSS</b>",
        email="safe@example.com",
        company_name="<img src=x onerror=alert(1)> Corp",
        job_title="<marquee>CEO</marquee>"
    )
    test_db.add(lead)
    test_db.commit()

    response = auth_client.get("/leads")
    assert response.status_code == 200
    raw_html = response.text
    # Raw unescaped dangerous tags must NOT be present
    assert "<script>alert(1)</script>" not in raw_html
    assert "<img src=x onerror=alert(1)>" not in raw_html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in raw_html
    assert "&lt;img src=x onerror=alert(1)&gt; Corp" in raw_html


def test_tc_leads_16_active_navigation_link_state(auth_client):
    """TC-LEADS-16: When visiting /leads, the base navigation link is marked active."""
    response = auth_client.get("/leads")
    assert response.status_code == 200
    html = response.text
    assert '<a href="/leads" class="nav-link active">Leads</a>' in html


def test_tc_leads_17_filter_form_renders_with_clean_submission_contract(auth_client, client):
    """TC-LEADS-17: Filter form renders with clean submission handler and crm.js progressive enhancement."""
    # 1. Verify HTML form markup on /leads
    response = auth_client.get("/leads")
    assert response.status_code == 200
    assert 'class="leads-filter-form"' in response.text
    assert 'id="leads-filter-form"' in response.text
    assert 'onsubmit="return handleLeadsFilterSubmit(event, this);"' in response.text

    # 2. Verify crm.js static script contains the clean form serializer
    res_js = client.get("/static/js/crm.js")
    assert res_js.status_code == 200
    js_content = res_js.text
    assert "handleLeadsFilterSubmit" in js_content
    assert "URLSearchParams" in js_content
    assert "form:not(.leads-filter-form)" in js_content


def test_tc_leads_18_status_only_filtering(auth_client, test_db):
    """TC-LEADS-18: GET /leads?status=Qualified filters only matching status."""
    lead1 = Lead(
        first_name="Alpha", last_name="Lead", email="alpha@example.com",
        company_name="Alpha Inc", status=LeadStatus.QUALIFIED
    )
    lead2 = Lead(
        first_name="Beta", last_name="Lead", email="beta@example.com",
        company_name="Beta Inc", status=LeadStatus.NEW
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    response = auth_client.get("/leads?status=Qualified")
    assert response.status_code == 200
    assert "Alpha Inc" in response.text
    assert "Beta Inc" not in response.text


def test_tc_leads_19_industry_only_filtering(auth_client, test_db):
    """TC-LEADS-19: GET /leads?industry=Technology filters only matching industry."""
    lead1 = Lead(
        first_name="Tech", last_name="Lead", email="tech@example.com",
        company_name="Tech Solutions", industry="Technology"
    )
    lead2 = Lead(
        first_name="Retail", last_name="Lead", email="retail@example.com",
        company_name="Retail Mart", industry="Retail"
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    response = auth_client.get("/leads?industry=Technology")
    assert response.status_code == 200
    assert "Tech Solutions" in response.text
    assert "Retail Mart" not in response.text


def test_tc_leads_20_min_score_only_filtering(auth_client, test_db):
    """TC-LEADS-20: GET /leads?min_score=75 filters only leads with score >= 75."""
    lead1 = Lead(
        first_name="High", last_name="Score", email="high@example.com",
        company_name="High Priority Co", qualification_score=85
    )
    lead2 = Lead(
        first_name="Low", last_name="Score", email="low@example.com",
        company_name="Low Priority Co", qualification_score=40
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    response = auth_client.get("/leads?min_score=75")
    assert response.status_code == 200
    assert "High Priority Co" in response.text
    assert "Low Priority Co" not in response.text


def test_tc_leads_21_search_only_filtering(auth_client, test_db):
    """TC-LEADS-21: GET /leads?search=Acme filters only matching search term."""
    lead1 = Lead(
        first_name="Wile", last_name="Coyote", email="coyote@acme.example.com",
        company_name="Acme Corp"
    )
    lead2 = Lead(
        first_name="Road", last_name="Runner", email="runner@desert.example.com",
        company_name="Desert Fast Co"
    )
    test_db.add_all([lead1, lead2])
    test_db.commit()

    response = auth_client.get("/leads?search=Acme")
    assert response.status_code == 200
    assert "Acme Corp" in response.text
    assert "Desert Fast Co" not in response.text


def test_tc_leads_22_multiple_filters_and_sorting(auth_client, test_db):
    """TC-LEADS-22: GET /leads with multiple filters and custom sorting."""
    lead1 = Lead(
        first_name="Wile", last_name="Coyote", email="coyote@acme.example.com",
        company_name="Acme Corp", status=LeadStatus.QUALIFIED,
        qualification_score=85, annual_revenue=1500000.0
    )
    lead2 = Lead(
        first_name="Sylvester", last_name="Cat", email="sylvester@acme.example.com",
        company_name="Acme Holdings", status=LeadStatus.QUALIFIED,
        qualification_score=95, annual_revenue=2500000.0
    )
    lead3 = Lead(
        first_name="Bugs", last_name="Bunny", email="bugs@other.example.com",
        company_name="Other Corp", status=LeadStatus.NEW,
        qualification_score=90
    )
    test_db.add_all([lead1, lead2, lead3])
    test_db.commit()

    url = "/leads?search=Acme&status=Qualified&min_score=75&sort_by=qualification_score&sort_order=desc"
    response = auth_client.get(url)
    assert response.status_code == 200
    assert "Acme Holdings" in response.text
    assert "Acme Corp" in response.text
    assert "Other Corp" not in response.text
    sylvester_pos = response.text.find("Acme Holdings")
    coyote_pos = response.text.find("Acme Corp")
    assert sylvester_pos < coyote_pos


def test_tc_leads_23_invalid_non_empty_min_score_rejected_by_backend(auth_client):
    """TC-LEADS-23: Invalid non-empty min_score values (non-integer or out-of-range) return 422."""
    # Non-integer string
    res_str = auth_client.get("/leads?min_score=abc")
    assert res_str.status_code == 422

    # Below minimum (0)
    res_neg = auth_client.get("/leads?min_score=-5")
    assert res_neg.status_code == 422

    # Above maximum (100)
    res_high = auth_client.get("/leads?min_score=150")
    assert res_high.status_code == 422


def test_tc_leads_24_pagination_query_preservation_omits_empty_parameters(auth_client, test_db):
    """TC-LEADS-24: Pagination links preserve active filters and omit empty optional parameters."""
    leads = [
        Lead(
            first_name=f"Lead{i:02d}",
            last_name="Test",
            email=f"lead{i:02d}@example.com",
            company_name=f"Company {i:02d}",
            status=LeadStatus.QUALIFIED,
            industry="Technology",
            qualification_score=80
        )
        for i in range(15)
    ]
    test_db.add_all(leads)
    test_db.commit()

    # Request with status and min_score but no search or industry
    response = auth_client.get("/leads?page=1&size=10&status=Qualified&min_score=75")
    assert response.status_code == 200
    assert "page=2" in response.text
    assert "status=Qualified" in response.text
    assert "min_score=75" in response.text
    # Empty parameters must NOT be present in pagination URLs
    assert "search=" not in response.text
    assert "industry=" not in response.text


def test_tc_leads_25_reset_filters_clean_url(auth_client, test_db):
    """TC-LEADS-25: When filters are active, Reset Filters links cleanly to /leads."""
    lead = Lead(
        first_name="Active",
        last_name="Filter",
        email="active@example.com",
        company_name="Active Filter Co",
        status=LeadStatus.QUALIFIED
    )
    test_db.add(lead)
    test_db.commit()

    response = auth_client.get("/leads?status=Qualified")
    assert response.status_code == 200
    assert 'href="/leads" class="btn btn-outline btn-sm" id="reset-filters-btn">Reset Filters</a>' in response.text
