import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum, Text, Boolean
from sqlalchemy.orm import relationship
import enum
from app.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    REP = "rep"


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.REP, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class LeadStatus(str, enum.Enum):
    NEW = "New"
    CONTACTED = "Contacted"
    QUALIFIED = "Qualified"
    UNQUALIFIED = "Unqualified"
    PROPOSAL_SENT = "Proposal Sent"
    WON = "Won"
    LOST = "Lost"


class LeadPriority(str, enum.Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    URGENT = "Urgent"


class ActivityType(str, enum.Enum):
    NOTE = "Note"
    CALL = "Call"
    EMAIL = "Email"
    MEETING = "Meeting"
    STATUS_CHANGE = "Status Change"



class Lead(Base):
    __tablename__ = "leads"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    company_name = Column(String(200), nullable=False)
    job_title = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True, index=True)
    company_size = Column(Integer, default=1)
    annual_revenue = Column(Float, default=0.0)
    
    status = Column(SQLEnum(LeadStatus), default=LeadStatus.NEW, index=True)
    priority = Column(SQLEnum(LeadPriority), default=LeadPriority.MEDIUM)
    qualification_score = Column(Integer, default=0, index=True)
    assigned_owner = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    activities = relationship("ActivityLog", back_populates="lead", cascade="all, delete-orphan")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False, index=True)
    activity_type = Column(SQLEnum(ActivityType), nullable=False)
    description = Column(Text, nullable=False)
    performed_by = Column(String(100), default="System")
    created_at = Column(DateTime, default=utc_now, nullable=False)

    lead = relationship("Lead", back_populates="activities")
