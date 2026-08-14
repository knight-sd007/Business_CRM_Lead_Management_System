import pytest
from app.models import Lead, LeadPriority
from app.services.scoring_engine import calculate_lead_qualification_score


def test_scoring_max_points():
    lead = Lead(
        first_name="Alice",
        last_name="CEO",
        email="alice@techgiant.example.com",
        company_name="Tech Giant Inc",
        job_title="Chief Executive Officer",
        industry="Technology",
        company_size=1000,
        annual_revenue=5000000.0
    )
    score, priority, factors = calculate_lead_qualification_score(lead)
    assert score == 100
    assert priority == LeadPriority.URGENT
    assert factors == {
        "annual_revenue": 30,
        "company_size": 25,
        "job_title": 25,
        "industry": 20
    }


def test_scoring_minimum_points():
    lead = Lead(
        first_name="Bob",
        last_name="User",
        email="bob@smallshop.example.com",
        company_name="Small Shop",
        job_title="Intern",
        industry="Agriculture",
        company_size=2,
        annual_revenue=10000.0
    )
    score, priority, factors = calculate_lead_qualification_score(lead)
    # Revenue: 5, Size: 5, Title: 5, Industry: 10 = 25
    assert score == 25
    assert priority == LeadPriority.LOW
    assert factors == {
        "annual_revenue": 5,
        "company_size": 5,
        "job_title": 5,
        "industry": 10
    }


def test_scoring_tier_mid_points():
    lead = Lead(
        first_name="Charlie",
        last_name="Manager",
        email="charlie@midco.example.com",
        company_name="MidCo Solutions",
        job_title="Engineering Manager",
        industry="Healthcare",
        company_size=75,
        annual_revenue=300000.0
    )
    score, priority, factors = calculate_lead_qualification_score(lead)
    # Revenue: 20 (>=250k), Size: 20 (>=50), Title: 15 (Manager), Industry: 20 (Healthcare) = 75
    assert score == 75
    assert priority == LeadPriority.URGENT
    assert factors["annual_revenue"] == 20
    assert factors["company_size"] == 20
    assert factors["job_title"] == 15
    assert factors["industry"] == 20
