from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models import LeadStatus, LeadPriority, ActivityType, UserRole


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.REP
    is_active: bool = True


class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    full_name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)
    role: Optional[UserRole] = UserRole.REP


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class LoginRequest(BaseModel):
    username_or_email: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse



class ActivityLogBase(BaseModel):
    activity_type: ActivityType
    description: str = Field(..., min_length=2, max_length=1000)
    performed_by: Optional[str] = "System"


class ActivityLogCreate(ActivityLogBase):
    pass


class ActivityLogResponse(ActivityLogBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    lead_id: str
    created_at: datetime


class LeadBase(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = None
    company_name: str = Field(..., min_length=1, max_length=200)
    job_title: Optional[str] = None
    industry: Optional[str] = "Technology"
    company_size: int = Field(default=10, ge=1)
    annual_revenue: float = Field(default=50000.0, ge=0.0)
    assigned_owner: Optional[str] = "Unassigned"
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    pass


class LeadUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[int] = None
    annual_revenue: Optional[float] = None
    status: Optional[LeadStatus] = None
    priority: Optional[LeadPriority] = None
    assigned_owner: Optional[str] = None
    notes: Optional[str] = None


class LeadResponse(LeadBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: LeadStatus
    priority: LeadPriority
    qualification_score: int
    created_at: datetime
    updated_at: datetime
    activities: List[ActivityLogResponse] = []


class PaginatedLeadResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[LeadResponse]


class LeadScoreBreakdown(BaseModel):
    lead_id: str
    qualification_score: int
    rating: str
    factors: dict
