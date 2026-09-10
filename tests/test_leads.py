import pytest


def test_create_lead_success(auth_client):
    payload = {
        "first_name": "Sarah",
        "last_name": "Connor",
        "email": "sarah.connor@cyberdyne.example.com",
        "company_name": "Cyberdyne Systems",
        "job_title": "Chief Technology Officer",
        "industry": "Technology",
        "company_size": 150,
        "annual_revenue": 500000.0,
        "assigned_owner": "Alex Rivera"
    }
    response = auth_client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == "Sarah"
    assert data["last_name"] == "Connor"
    assert data["email"] == "sarah.connor@cyberdyne.example.com"
    assert data["qualification_score"] >= 75
    assert data["priority"] == "Urgent"
    assert data["status"] == "New"
    assert len(data["activities"]) == 1
    assert "Lead created with qualification score" in data["activities"][0]["description"]


def test_create_lead_validation_failure(auth_client):
    # Invalid email
    payload = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "invalid-email-string",
        "company_name": "Acme Corp"
    }
    response = auth_client.post("/api/v1/leads", json=payload)
    assert response.status_code == 422

    # Negative company size
    payload_size = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john@example.com",
        "company_name": "Acme Corp",
        "company_size": -5
    }
    response_size = auth_client.post("/api/v1/leads", json=payload_size)
    assert response_size.status_code == 422


def test_get_lead_by_id(auth_client):
    create_res = auth_client.post("/api/v1/leads", json={
        "first_name": "Marcus",
        "last_name": "Vance",
        "email": "marcus.vance@apexcloud.example.com",
        "company_name": "Apex Cloud Dynamics"
    })
    lead_id = create_res.json()["id"]

    get_res = auth_client.get(f"/api/v1/leads/{lead_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == lead_id


def test_get_lead_not_found(auth_client):
    response = auth_client.get("/api/v1/leads/non-existent-uuid-1234")
    assert response.status_code == 404
    assert response.json()["detail"] == "Lead not found."


def test_update_lead_and_activity_log(auth_client):
    create_res = auth_client.post("/api/v1/leads", json={
        "first_name": "Elena",
        "last_name": "Rostova",
        "email": "elena.r@biogencorp.example.com",
        "company_name": "BioGen Innovations"
    })
    lead_id = create_res.json()["id"]

    # Update status to Qualified
    update_res = auth_client.put(f"/api/v1/leads/{lead_id}", json={"status": "Qualified"})
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "Qualified"

    # Verify status change activity logged
    get_res = auth_client.get(f"/api/v1/leads/{lead_id}")
    activities = get_res.json()["activities"]
    assert len(activities) == 2
    assert activities[1]["activity_type"] == "Status Change"
    assert "Status changed from 'New' to 'Qualified'" in activities[1]["description"]


def test_update_lead_not_found(auth_client):
    response = auth_client.put("/api/v1/leads/non-existent-uuid", json={"first_name": "NewName"})
    assert response.status_code == 404


def test_delete_lead_success_admin(auth_client):
    create_res = auth_client.post("/api/v1/leads", json={
        "first_name": "David",
        "last_name": "Chen",
        "email": "d.chen@fintechlabs.example.com",
        "company_name": "FinTech Labs"
    })
    lead_id = create_res.json()["id"]

    del_res = auth_client.delete(f"/api/v1/leads/{lead_id}")
    assert del_res.status_code == 204

    get_res = auth_client.get(f"/api/v1/leads/{lead_id}")
    assert get_res.status_code == 404


def test_delete_lead_success_manager(manager_client, auth_client):
    create_res = auth_client.post("/api/v1/leads", json={
        "first_name": "Manager",
        "last_name": "DeleteTest",
        "email": "mgr.del@example.com",
        "company_name": "Mgr Co"
    })
    lead_id = create_res.json()["id"]

    del_res = manager_client.delete(f"/api/v1/leads/{lead_id}")
    assert del_res.status_code == 204


def test_delete_lead_forbidden_for_sales_rep(rep_client, auth_client):
    create_res = auth_client.post("/api/v1/leads", json={
        "first_name": "Protected",
        "last_name": "Lead",
        "email": "protected@example.com",
        "company_name": "Protected Corp"
    })
    lead_id = create_res.json()["id"]

    # Sales Rep should receive 403 Forbidden when attempting deletion
    del_res = rep_client.delete(f"/api/v1/leads/{lead_id}")
    assert del_res.status_code == 403
    assert "insufficient role permissions" in del_res.json()["detail"].lower()


def test_delete_lead_not_found(auth_client):
    response = auth_client.delete("/api/v1/leads/non-existent-uuid")
    assert response.status_code == 404


def test_list_leads_pagination_and_filtering(auth_client):
    for i in range(15):
        auth_client.post("/api/v1/leads", json={
            "first_name": f"User{i}",
            "last_name": "Test",
            "email": f"user{i}@example.com",
            "company_name": f"Company{i}",
            "industry": "Software" if i % 2 == 0 else "Finance",
            "company_size": 10 + i,
            "annual_revenue": 10000.0 * i
        })

    # Page 1
    res1 = auth_client.get("/api/v1/leads?page=1&size=10")
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["total"] == 15
    assert data1["page"] == 1
    assert data1["size"] == 10
    assert len(data1["items"]) == 10

    # Filter by industry
    res_ind = auth_client.get("/api/v1/leads?industry=Software")
    assert res_ind.status_code == 200
    assert res_ind.json()["total"] == 8

    # Search filter
    res_search = auth_client.get("/api/v1/leads?search=User1")
    assert res_search.status_code == 200
    assert res_search.json()["total"] >= 1


def test_lead_sorting(auth_client):
    auth_client.post("/api/v1/leads", json={
        "first_name": "Alpha",
        "last_name": "One",
        "email": "alpha@example.com",
        "company_name": "Alpha Co",
        "annual_revenue": 100000.0
    })
    auth_client.post("/api/v1/leads", json={
        "first_name": "Beta",
        "last_name": "Two",
        "email": "beta@example.com",
        "company_name": "Beta Co",
        "annual_revenue": 500000.0
    })

    res_desc = auth_client.get("/api/v1/leads?sort_by=annual_revenue&sort_order=desc")
    assert res_desc.status_code == 200
    items_desc = res_desc.json()["items"]
    assert items_desc[0]["annual_revenue"] >= items_desc[1]["annual_revenue"]


def test_export_leads_csv(auth_client):
    auth_client.post("/api/v1/leads", json={
        "first_name": "Jane",
        "last_name": "Smith",
        "email": "jane@smith.example.com",
        "company_name": "Tech Solutions"
    })
    response = auth_client.get("/api/v1/leads/export/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "First Name,Last Name,Email" in response.text
    assert "Jane,Smith,jane@smith.example.com" in response.text


def test_score_breakdown_endpoint(auth_client):
    create_res = auth_client.post("/api/v1/leads", json={
        "first_name": "Rachel",
        "last_name": "Green",
        "email": "rachel.g@retailplus.example.com",
        "company_name": "RetailPlus",
        "job_title": "CEO",
        "industry": "Technology",
        "company_size": 600,
        "annual_revenue": 2000000.0
    })
    lead_id = create_res.json()["id"]

    res = auth_client.get(f"/api/v1/leads/{lead_id}/score-breakdown")
    assert res.status_code == 200
    data = res.json()
    assert data["lead_id"] == lead_id
    assert data["qualification_score"] == 100
    assert data["rating"] == "Urgent"
    assert data["factors"]["annual_revenue"] == 30
    assert data["factors"]["company_size"] == 25
    assert data["factors"]["job_title"] == 25
    assert data["factors"]["industry"] == 20


def test_add_activity_endpoint(auth_client):
    create_res = auth_client.post("/api/v1/leads", json={
        "first_name": "Tom",
        "last_name": "Hardy",
        "email": "tom@example.com",
        "company_name": "Hardy Media"
    })
    lead_id = create_res.json()["id"]

    act_payload = {
        "activity_type": "Call",
        "description": "Followed up regarding annual licensing terms.",
        "performed_by": "Alex Rivera"
    }
    act_res = auth_client.post(f"/api/v1/leads/{lead_id}/activities", json=act_payload)
    assert act_res.status_code == 201
    act_data = act_res.json()
    assert act_data["activity_type"] == "Call"
    assert act_data["description"] == "Followed up regarding annual licensing terms."
    assert act_data["performed_by"] == "Alex Rivera"


def test_unauthenticated_endpoints_return_401(client):
    """Verify all protected CRM endpoints reject unauthenticated requests with HTTP 401."""
    endpoints = [
        ("GET", "/api/v1/leads"),
        ("POST", "/api/v1/leads"),
        ("GET", "/api/v1/leads/export/csv"),
        ("GET", "/api/v1/leads/test-id-123"),
        ("PUT", "/api/v1/leads/test-id-123"),
        ("DELETE", "/api/v1/leads/test-id-123"),
        ("GET", "/api/v1/leads/test-id-123/score-breakdown"),
        ("POST", "/api/v1/leads/test-id-123/activities")
    ]

    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "POST":
            res = client.post(path, json={})
        elif method == "PUT":
            res = client.put(path, json={})
        elif method == "DELETE":
            res = client.delete(path)

        assert res.status_code == 401, f"Expected 401 for {method} {path}, got {res.status_code}"
        assert "authentication credentials required" in res.json()["detail"].lower() or "not found" in res.json()["detail"].lower()
