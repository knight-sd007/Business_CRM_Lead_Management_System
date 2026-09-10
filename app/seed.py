"""
Synthetic Seed Script for Business CRM Lead Management System.
Populates the local database with safe, realistic synthetic demo data and test users.
"""

from app.database import SessionLocal, engine, Base
from app.models import Lead, ActivityLog, LeadStatus, LeadPriority, ActivityType, User, UserRole
from app.services.scoring_engine import calculate_lead_qualification_score
from app.services.auth_service import hash_password

SYNTHETIC_USERS = [
    {
        "email": "admin@crm.example.com",
        "username": "admin",
        "full_name": "CRM Administrator",
        "role": UserRole.ADMIN,
        "password": "AdminPassword123!"
    },
    {
        "email": "manager@crm.example.com",
        "username": "manager",
        "full_name": "Sales Manager",
        "role": UserRole.MANAGER,
        "password": "ManagerPassword123!"
    },
    {
        "email": "rep@crm.example.com",
        "username": "salesrep",
        "full_name": "Alex Rivera",
        "role": UserRole.REP,
        "password": "RepPassword123!"
    }
]

SYNTHETIC_LEADS = [
    {
        "first_name": "Sarah",
        "last_name": "Connor",
        "email": "sarah.connor@cyberdyne.example.com",
        "phone": "+1-555-0100",
        "company_name": "Cyberdyne Systems",
        "job_title": "Chief Technology Officer",
        "industry": "Technology",
        "company_size": 250,
        "annual_revenue": 1500000.0,
        "assigned_owner": "Alex Rivera",
        "status": LeadStatus.QUALIFIED,
        "notes": "Interested in enterprise CRM migration and security compliance features."
    },
    {
        "first_name": "Marcus",
        "last_name": "Vance",
        "email": "marcus.vance@apexcloud.example.com",
        "phone": "+1-555-0101",
        "company_name": "Apex Cloud Dynamics",
        "job_title": "VP of Operations",
        "industry": "Software",
        "company_size": 120,
        "annual_revenue": 600000.0,
        "assigned_owner": "Alex Rivera",
        "status": LeadStatus.NEW,
        "notes": "Requested product demo via website contact form."
    },
    {
        "first_name": "Elena",
        "last_name": "Rostova",
        "email": "elena.r@biogencorp.example.com",
        "phone": "+1-555-0102",
        "company_name": "BioGen Innovations",
        "job_title": "Director of IT",
        "industry": "Healthcare",
        "company_size": 600,
        "annual_revenue": 3500000.0,
        "assigned_owner": "Jordan Lee",
        "status": LeadStatus.PROPOSAL_SENT,
        "notes": "Proposal sent on Monday. Follow-up meeting scheduled next week."
    },
    {
        "first_name": "David",
        "last_name": "Chen",
        "email": "d.chen@fintechlabs.example.com",
        "phone": "+1-555-0103",
        "company_name": "FinTech Labs",
        "job_title": "Engineering Lead",
        "industry": "Finance",
        "company_size": 45,
        "annual_revenue": 180000.0,
        "assigned_owner": "Jordan Lee",
        "status": LeadStatus.CONTACTED,
        "notes": "Discussing API integration requirements."
    },
    {
        "first_name": "Rachel",
        "last_name": "Green",
        "email": "rachel.g@retailplus.example.com",
        "phone": "+1-555-0104",
        "company_name": "RetailPlus Logistics",
        "job_title": "Logistics Analyst",
        "industry": "E-Commerce",
        "company_size": 8,
        "annual_revenue": 35000.0,
        "assigned_owner": "Unassigned",
        "status": LeadStatus.UNQUALIFIED,
        "notes": "Company size below current target segment minimum threshold."
    }
]


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Seed Users
        if db.query(User).count() == 0:
            print("Seeding synthetic users into database...")
            for user_data in SYNTHETIC_USERS:
                raw_pwd = user_data["password"]
                user = User(
                    email=user_data["email"],
                    username=user_data["username"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    password_hash=hash_password(raw_pwd),
                    is_active=True
                )
                db.add(user)
            db.commit()
            print(f"Successfully seeded {len(SYNTHETIC_USERS)} users.")

        # Seed Leads
        if db.query(Lead).count() == 0:
            print("Seeding synthetic leads into database...")
            for lead_data in SYNTHETIC_LEADS:
                lead = Lead(**lead_data)
                score, priority, _ = calculate_lead_qualification_score(lead)
                lead.qualification_score = score
                lead.priority = priority

                db.add(lead)
                db.commit()
                db.refresh(lead)

                activity = ActivityLog(
                    lead_id=lead.id,
                    activity_type=ActivityType.NOTE,
                    description=f"Synthetic demo lead seeded. Initial score: {score} ({priority.value}).",
                    performed_by="Seed Script"
                )
                db.add(activity)
                db.commit()

            print(f"Successfully seeded {len(SYNTHETIC_LEADS)} synthetic leads into database.")
        else:
            print("Leads already exist in database. Skipping lead seed operation.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
