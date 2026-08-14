# Business CRM Lead Management System

An enterprise REST API built with Python 3.12 and FastAPI for automated lead ingestion, algorithmic lead qualification scoring, pipeline tracking, activity audit logging, paginated multi-criteria filtering, and CSV reporting.

---

## Problem Statement

Sales organizations often struggle with inefficient lead triage, manual scoring bottlenecks, and fragmented communication audit trails. Without automated qualification logic, high-value enterprise leads risk sitting in unassigned queues while sales representatives spend time on low-yield prospects.

The **Business CRM Lead Management System** solves these operational challenges by providing:
1. **Automated Lead Qualification & Priority Triage**: A deterministic scoring engine evaluating company size, annual revenue, buyer title seniority, and target industry alignment.
2. **Activity Audit Trail**: Structured logging of calls, meetings, status changes, and notes for transparent pipeline tracking.
3. **High-Performance Querying & Reporting**: Paginated search, multi-field filtering, sorting, and streaming CSV data exports.

---

## Capabilities

- **Lead Ingestion & Auto-Scoring**: Automatic score calculation (0–100) and priority categorization (`Urgent`, `High`, `Medium`, `Low`) upon creation and field updates.
- **Activity Log Audit**: Automatic logging of lead creation and status changes, plus endpoints for custom sales team activity entries.
- **Paginated Search & Filtering**: Multi-criteria query filters by status, industry substring, minimum qualification score, and keyword search across names, emails, and companies.
- **Dynamic Sorting**: Sorting support across `created_at`, `qualification_score`, `annual_revenue`, and `company_size` in ascending or descending order.
- **CSV Data Export**: Streamed CSV export endpoint for pipeline analysis in BI tools or spreadsheets.
- **Synthetic Data Seeding**: CLI seed utility (`python -m app.seed`) generating safe, realistic demonstration data.

---

## Tech Stack

- **Language & Runtime**: Python 3.12
- **Web Framework**: FastAPI (v0.110+)
- **ASGI Server**: Uvicorn
- **ORM & Database**: SQLAlchemy 2.0 with SQLite (local/demo) and PostgreSQL support
- **Schema Validation**: Pydantic v2 (with email validation)
- **Environment Management**: `python-dotenv` & `pydantic-settings`
- **Test Suite**: Pytest with HTTPX and SQLite in-memory fixtures

---

## Architecture

```text
                                 [ Client / HTTP Request ]
                                             │
                                             ▼
                              [ FastAPI Router (/api/v1/leads) ]
                                             │
                                             ▼
                             [ Pydantic v2 Input Validation ]
                                             │
                                             ▼
                        ┌────────────────────┴────────────────────┐
                        │                                         │
                        ▼                                         ▼
         [ Qualification Scoring Engine ]               [ Lead Service Layer ]
        (Revenue, Size, Title, Industry)                          │
                        │                                         │
                        └────────────────────┬────────────────────┘
                                             │
                                             ▼
                          [ SQLAlchemy ORM Models & Session ]
                                             │
                                             ▼
                              [ SQLite / PostgreSQL Database ]
```

---

## Project Structure

```text
Portfolio_02/
├── app/
│   ├── __init__.py
│   ├── config.py           # Application configuration & .env loader
│   ├── database.py         # SQLAlchemy engine, session maker, DB dependency
│   ├── main.py             # FastAPI entrypoint, CORS, global exception handler
│   ├── models.py           # SQLAlchemy ORM models (Lead, ActivityLog)
│   ├── schemas.py          # Pydantic request/response validation schemas
│   ├── seed.py             # Synthetic demo data seed script
│   ├── routers/
│   │   ├── __init__.py
│   │   └── leads.py        # Lead API endpoint routes
│   └── services/
│       ├── __init__.py
│       ├── lead_service.py # Core business logic & database queries
│       └── scoring_engine.py # Lead qualification scoring rules engine
├── tests/
│   ├── conftest.py         # In-memory database fixtures & TestClient
│   ├── test_config.py      # Configuration resolution & env override tests
│   ├── test_health.py      # Health check endpoint tests
│   ├── test_leads.py       # Lead CRUD, pagination, sorting & CSV tests
│   ├── test_scoring.py     # Scoring algorithm unit tests
│   └── test_security.py    # SQL injection, path traversal & error isolation tests
├── .env.example            # Environment configuration template
├── .gitignore              # Git exclusion rules
├── Dockerfile              # Container deployment file
├── docker-compose.yml      # Local multi-container compose file
├── pyproject.toml          # Build backend and Pytest configuration
├── README.md               # Project documentation
└── requirements.txt        # Python dependency manifest
```

---

## API Overview

Interactive Swagger / OpenAPI documentation is automatically available at `/docs` when running the application.

| HTTP Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Application health and status check |
| `POST` | `/api/v1/leads` | Create lead with automatic score & priority calculation |
| `GET` | `/api/v1/leads` | Paginated lead list with filtering & sorting |
| `GET` | `/api/v1/leads/export/csv` | Download pipeline leads as CSV report |
| `GET` | `/api/v1/leads/{lead_id}` | Get lead details and activity audit history |
| `PUT` | `/api/v1/leads/{lead_id}` | Update lead details, recalculating score on field changes |
| `DELETE` | `/api/v1/leads/{lead_id}` | Delete lead and associated activity logs |
| `GET` | `/api/v1/leads/{lead_id}/score-breakdown` | Get detailed itemized score factors breakdown |
| `POST` | `/api/v1/leads/{lead_id}/activities` | Record custom activity log (Call, Note, Meeting, Email) |

### Request Example: Create Lead

```json
POST /api/v1/leads
Content-Type: application/json

{
  "first_name": "Sarah",
  "last_name": "Connor",
  "email": "sarah.connor@cyberdyne.example.com",
  "company_name": "Cyberdyne Systems",
  "job_title": "Chief Technology Officer",
  "industry": "Technology",
  "company_size": 250,
  "annual_revenue": 1500000.0,
  "assigned_owner": "Alex Rivera",
  "notes": "Exploring enterprise lead management modernization."
}
```

### Response Example: Create Lead

```json
{
  "first_name": "Sarah",
  "last_name": "Connor",
  "email": "sarah.connor@cyberdyne.example.com",
  "phone": null,
  "company_name": "Cyberdyne Systems",
  "job_title": "Chief Technology Officer",
  "industry": "Technology",
  "company_size": 250,
  "annual_revenue": 1500000.0,
  "assigned_owner": "Alex Rivera",
  "notes": "Exploring enterprise lead management modernization.",
  "id": "c1f7a240-8f92-4d1a-b328-98e82a201cbf",
  "status": "New",
  "priority": "Urgent",
  "qualification_score": 100,
  "created_at": "2026-08-15T00:00:00Z",
  "updated_at": "2026-08-15T00:00:00Z",
  "activities": [
    {
      "activity_type": "Note",
      "description": "Lead created with qualification score 100 (Urgent priority).",
      "performed_by": "Alex Rivera",
      "id": "e4a8b291-7d12-4091-a876-091f32a22c01",
      "lead_id": "c1f7a240-8f92-4d1a-b328-98e82a201cbf",
      "created_at": "2026-08-15T00:00:00Z"
    }
  ]
}
```

---

## Database

The application uses SQLAlchemy 2.0 ORM to interact with SQLite for local development and testing, and can seamlessly connect to PostgreSQL in staging or production by supplying a PostgreSQL `DATABASE_URL`.

- **Database Files**: Generated `.db` SQLite database files are excluded from Git repository tracking via `.gitignore`.
- **Synthetic Demonstration Data**: To seed local development databases with safe, synthetic data:

```bash
python -m app.seed
```

---

## Configuration & .env Setup

The application reads configuration through Pydantic Settings and `python-dotenv`.

### Local Development Setup

1. Copy the environment configuration template:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` to set local development values.

> [!IMPORTANT]
> `.env` contains local environment settings and **MUST NOT** be committed to version control. It is explicitly listed in `.gitignore`.

For cloud or production deployments, secrets and configuration should be injected directly via environment variables or an enterprise secret management service (such as AWS Secrets Manager, HashiCorp Vault, or Azure Key Vault). `.env` is intended solely for local development convenance and is not a production secret management solution.

---

## Local Development

```bash
# 1. Create and activate Python 3.12 virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Setup local environment
cp .env.example .env

# 4. Seed synthetic demonstration data (optional)
python -m app.seed

# 5. Start development server
uvicorn app.main:app --reload --port 8000
```

Open `http://localhost:8000/docs` in your browser to test endpoints interactively.

---

## Testing

The test suite runs using Pytest with an in-memory SQLite database (`sqlite:///:memory:`) using SQLAlchemy's `StaticPool` to ensure 100% test isolation and zero database file contamination on disk.

```bash
# Run all tests
pytest

# Run tests with detailed coverage report
pytest --cov=app --cov-report=term-missing
```

---

## Security

- **Zero Hardcoded Secrets**: All configuration values are loaded dynamically from environment variables.
- **SQL Injection Defense**: Built on SQLAlchemy ORM using parameterized queries.
- **Input Validation**: Strict schema enforcement using Pydantic v2 and EmailStr validators.
- **Error Traceback Isolation**: Global exception handlers suppress internal database paths and stack traces from production client HTTP responses.
- **CORS Hardening**: Configurable origin controls parsed from environment settings.

---

## Limitations

- **Local Single-Tenant Scope**: Current architecture is single-tenant without multi-organization workspace partitioning.
- **Basic Authentication**: Auth middleware is currently out-of-scope for local demonstration; access control should be paired with an API gateway or JWT auth middleware for multi-user production environments.
