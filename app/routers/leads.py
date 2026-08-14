import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import LeadStatus
from app.schemas import (
    LeadCreate, LeadUpdate, LeadResponse, PaginatedLeadResponse,
    ActivityLogCreate, ActivityLogResponse, LeadScoreBreakdown
)
from app.services.lead_service import LeadService
from app.services.scoring_engine import calculate_lead_qualification_score

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.post("", response_model=LeadResponse, status_code=status.HTTP_201_CREATED)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    service = LeadService(db)
    return service.create_lead(payload)


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
    db: Session = Depends(get_db)
):
    service = LeadService(db)
    return service.get_leads_paginated(
        page=page, size=size, status=status_filter, industry=industry,
        min_score=min_score, search=search, sort_by=sort_by, sort_order=sort_order
    )


@router.get("/export/csv")
def export_leads_csv(db: Session = Depends(get_db)):
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
            lead.id, lead.first_name, lead.last_name, lead.email, lead.company_name,
            lead.job_title or "", lead.industry or "", lead.annual_revenue,
            lead.qualification_score, lead.status.value, lead.priority.value,
            lead.assigned_owner or "", lead.created_at.isoformat()
        ])

    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads_export.csv"}
    )


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.get_lead(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: str, payload: LeadUpdate, db: Session = Depends(get_db)):
    service = LeadService(db)
    lead = service.update_lead(lead_id, payload)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(lead_id: str, db: Session = Depends(get_db)):
    service = LeadService(db)
    success = service.delete_lead(lead_id)
    if not success:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{lead_id}/score-breakdown", response_model=LeadScoreBreakdown)
def get_score_breakdown(lead_id: str, db: Session = Depends(get_db)):
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
def add_activity(lead_id: str, payload: ActivityLogCreate, db: Session = Depends(get_db)):
    service = LeadService(db)
    activity = service.add_activity(lead_id, payload)
    if not activity:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return activity
