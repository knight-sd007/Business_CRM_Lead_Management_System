from app.models import Lead, LeadPriority


def calculate_lead_qualification_score(lead: Lead) -> tuple[int, LeadPriority, dict]:
    """
    Computes a lead qualification score (0-100) based on key business metrics:
    - Annual Revenue (Up to 30 points)
    - Company Size (Up to 25 points)
    - Job Title Seniority (Up to 25 points)
    - Industry Match (Up to 20 points)
    """
    score = 0
    factors = {}

    # 1. Annual Revenue Scoring (Max 30 pts)
    revenue = lead.annual_revenue or 0.0
    if revenue >= 1000000:
        rev_score = 30
    elif revenue >= 250000:
        rev_score = 20
    elif revenue >= 50000:
        rev_score = 10
    else:
        rev_score = 5
    score += rev_score
    factors["annual_revenue"] = rev_score

    # 2. Company Size Scoring (Max 25 pts)
    size = lead.company_size or 1
    if size >= 500:
        size_score = 25
    elif size >= 50:
        size_score = 20
    elif size >= 10:
        size_score = 10
    else:
        size_score = 5
    score += size_score
    factors["company_size"] = size_score

    # 3. Job Title Seniority Scoring (Max 25 pts)
    title = (lead.job_title or "").lower()
    c_level_keywords = ["ceo", "cto", "cfo", "chief", "officer", "vp", "vice president", "president", "founder", "director"]
    if any(keyword in title for keyword in c_level_keywords):
        title_score = 25
    elif any(keyword in title for keyword in ["manager", "lead", "head"]):
        title_score = 15
    elif any(keyword in title for keyword in ["engineer", "analyst", "specialist"]):
        title_score = 10
    else:
        title_score = 5
    score += title_score
    factors["job_title"] = title_score

    # 4. Target Industry Match (Max 20 pts)
    industry = (lead.industry or "").lower()
    target_industries = ["technology", "software", "finance", "healthcare", "e-commerce"]
    if any(ind in industry for ind in target_industries):
        ind_score = 20
    else:
        ind_score = 10
    score += ind_score
    factors["industry"] = ind_score

    # Determine Priority based on total score
    if score >= 75:
        priority = LeadPriority.URGENT
    elif score >= 50:
        priority = LeadPriority.HIGH
    elif score >= 30:
        priority = LeadPriority.MEDIUM
    else:
        priority = LeadPriority.LOW

    return score, priority, factors
