import csv
import io
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LeadStatus, User, UserRole
from app.schemas import (
    LeadCreate, LeadUpdate, LeadResponse, PaginatedLeadResponse,
    ActivityLogCreate, ActivityLogResponse, LeadScoreBreakdown
)
from app.services.lead_service import LeadService
from app.services.scoring_engine import calculate_lead_qualification_score
from app.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/leads", tags=["Leads"])

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n", "%")


def sanitize_csv_cell(value: Any) -> Any:
    """Neutralize potential CSV formula injection payloads by prepending a single quote."""
    if value is None:
        return ""
    if isinstance(value, str):
        if value.startswith(FORMULA_PREFIXES):
            return f"'{value}"
    return value


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    # Default performed_by to current authenticated user
    lead = service.create_lead(payload)
    return lead


@router.get("", response_model=PaginatedLeadResponse)
def list_leads(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    status_filter: Optional[LeadStatus] = Query(None, alias="status"),
    industry: Optional[str] = None,
    min_score: Optional[int] = Query(None, ge=0, le=100),
    search: Optional[str] = None,
    sort_by: str = Query("created_at", pattern="^(created_at|qualification_score|annual_revenue|company_size)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    return service.get_leads_paginated(
        page=page, size=size, status=status_filter, industry=industry,
        min_score=min_score, search=search, sort_by=sort_by, sort_order=sort_order
    )


@router.get("/export/csv")
def export_leads_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    leads_data = service.get_leads_paginated(page=1, size=10000)["items"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "First Name", "Last Name", "Email", "Company", "Job Title",
        "Industry", "Revenue", "Score", "Status", "Priority", "Owner", "Created At"
    ])

    for lead in leads_data:
        writer.writerow([
            sanitize_csv_cell(lead.id),
            sanitize_csv_cell(lead.first_name),
            sanitize_csv_cell(lead.last_name),
            sanitize_csv_cell(lead.email),
            sanitize_csv_cell(lead.company_name),
            sanitize_csv_cell(lead.job_title or ""),
            sanitize_csv_cell(lead.industry or ""),
            lead.annual_revenue,
            lead.qualification_score,
            lead.status.value,
            lead.priority.value,
            sanitize_csv_cell(lead.assigned_owner or ""),
            lead.created_at.isoformat()
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    lead = service.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    lead = service.update_lead(lead_id, payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.MANAGER)),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    success = service.delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{lead_id}/score-breakdown", response_model=LeadScoreBreakdown)
def get_score_breakdown(
    lead_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    lead = service.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")

    score, priority, factors = calculate_lead_qualification_score(lead)
    return LeadScoreBreakdown(
        lead_id=lead.id,
        qualification_score=score,
        rating=priority.value,
        factors=factors
    )


@router.post("/{lead_id}/activities", response_model=ActivityLogResponse, status_code=status.HTTP_201_CREATED)
def add_activity(
    lead_id: str,
    payload: ActivityLogCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    if payload.performed_by == "System" and current_user.full_name:
        payload.performed_by = current_user.full_name
    activity = service.add_activity(lead_id, payload)
    if not activity:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return activity
