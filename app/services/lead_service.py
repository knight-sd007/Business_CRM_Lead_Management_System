import math
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc
from app.models import Lead, ActivityLog, ActivityType, LeadStatus, LeadPriority
from app.schemas import LeadCreate, LeadUpdate, ActivityLogCreate
from app.services.scoring_engine import calculate_lead_qualification_score


class LeadService:
    def __init__(self, db: Session):
        self.db = db

    def create_lead(self, payload: LeadCreate) -> Lead:
        lead = Lead(**payload.model_dump())
        score, priority, _ = calculate_lead_qualification_score(lead)
        lead.qualification_score = score
        lead.priority = priority

        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)

        # Log initial creation activity
        activity = ActivityLog(
            lead_id=lead.id,
            activity_type=ActivityType.NOTE,
            description=f"Lead created with qualification score {score} ({priority.value} priority).",
            performed_by=lead.assigned_owner or "System"
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(lead)

        return lead

    def get_lead(self, lead_id: str) -> Optional[Lead]:
        return self.db.query(Lead).filter(Lead.id == lead_id).first()

    def get_leads_paginated(
        self,
        page: int = 1,
        size: int = 10,
        status: Optional[LeadStatus] = None,
        industry: Optional[str] = None,
        min_score: Optional[int] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ):
        query = self.db.query(Lead)

        if status:
            query = query.filter(Lead.status == status)
        if industry:
            query = query.filter(Lead.industry.ilike(f"%{industry}%"))
        if min_score is not None:
            query = query.filter(Lead.qualification_score >= min_score)
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    Lead.first_name.ilike(search_pattern),
                    Lead.last_name.ilike(search_pattern),
                    Lead.email.ilike(search_pattern),
                    Lead.company_name.ilike(search_pattern)
                )
            )

        total = query.count()
        pages = math.ceil(total / size) if total > 0 else 1

        sort_col = getattr(Lead, sort_by, Lead.created_at)
        if sort_order.lower() == "asc":
            query = query.order_by(asc(sort_col))
        else:
            query = query.order_by(desc(sort_col))

        offset = (page - 1) * size
        items = query.offset(offset).limit(size).all()

        return {
            "total": total,
            "page": page,
            "size": size,
            "pages": pages,
            "items": items
        }

    def update_lead(self, lead_id: str, payload: LeadUpdate) -> Optional[Lead]:
        lead = self.get_lead(lead_id)
        if not lead:
            return None

        update_data = payload.model_dump(exclude_unset=True)
        old_status = lead.status

        for key, value in update_data.items():
            setattr(lead, key, value)

        # Recalculate qualification score on attribute updates
        score, priority, _ = calculate_lead_qualification_score(lead)
        lead.qualification_score = score
        if "priority" not in update_data:
            lead.priority = priority

        if "status" in update_data and update_data["status"] != old_status:
            activity = ActivityLog(
                lead_id=lead.id,
                activity_type=ActivityType.STATUS_CHANGE,
                description=f"Status changed from '{old_status.value}' to '{lead.status.value}'.",
                performed_by=lead.assigned_owner or "System"
            )
            self.db.add(activity)

        self.db.commit()
        self.db.refresh(lead)
        return lead

    def add_activity(self, lead_id: str, payload: ActivityLogCreate) -> Optional[ActivityLog]:
        lead = self.get_lead(lead_id)
        if not lead:
            return None

        activity = ActivityLog(
            lead_id=lead_id,
            **payload.model_dump()
        )
        self.db.add(activity)
        self.db.commit()
        self.db.refresh(activity)
        return activity

    def delete_lead(self, lead_id: str) -> bool:
        lead = self.get_lead(lead_id)
        if not lead:
            return False
        self.db.delete(lead)
        self.db.commit()
        return True
