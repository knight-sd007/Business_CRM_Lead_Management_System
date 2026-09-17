# Business CRM Lead Management System

An enterprise B2B CRM lead management platform built with Python 3.12, FastAPI, SQLAlchemy, and SQLite. The platform combines automated qualification scoring, audit activity logging, high-performance REST APIs, and a dark-glass server-rendered Web UI.

---

## 1. Executive Summary & Problem Statement

Sales teams frequently face operational bottlenecks from fragmented prospect tracking, manual lead qualification delays, and disconnected activity logs. Without automated triage logic, high-value opportunities risk sitting in unassigned queues while sales representatives spend time on low-yield prospects.

The **Business CRM Lead Management System** solves these challenges by providing:
1. **Algorithmic Lead Qualification & Priority Triage**: A deterministic scoring engine that automatically evaluates annual revenue, company size, buyer job title seniority, and target industry match to calculate a qualification score (0–100) and assign a priority (`Urgent`, `High`, `Medium`, `Low`).
2. **Comprehensive Activity & Status Audit Trail**: Structured event logging tracking lead creation, status updates, sales calls, meetings, emails, and qualification notes.
3. **Dual-Surface Architecture**: A programmatic REST API (`/api/v1/...`) alongside an authenticated, responsive server-rendered Web UI (`/dashboard`, `/leads`, `/leads/new`).
4. **Hardened Security & CI/CD Pipeline**: Multi-role RBAC, HMAC-SHA256 CSRF protection, secure HTTP-only session cookies, CSV formula-injection sanitization, Gitleaks secret scanning, Trivy container vulnerability scanning, and automated ARM64 deployment to Oracle Cloud Infrastructure (OCI) via Cloudflare Tunnels.

---

## 2. System Architecture

```text
                                  [ User / Browser Client ]        [ Programmatic REST Client ]
                                              │                                  │
                                              ▼                                  ▼
                                   [ Web UI Routes (web.py) ]        [ REST Routers (/api/v1) ]
                                   (CSRF, Cookies, Templates)        (Bearer Auth / JSON APIs)
                                              │                                  │
                                              └────────────────┬─────────────────┘
                                                               │
                                                               ▼
                                                [ FastAPI Application Layer ]
                                                (CORS, Security Headers, Auth)
                                                               │
                                                               ▼
                                                [ Pydantic v2 Schema Validation ]
                                                (LeadCreate, LeadUpdate, Auth)
                                                               │
                                                               ▼
                                                [ Lead & Auth Service Layers ]
                                                               │
                                            ┌──────────────────┴──────────────────┐
                                            │                                     │
                                            ▼                                     ▼
                             [ Qualification Scoring Engine ]          [ SQLAlchemy 2.0 ORM ]
                             (Revenue, Size, Title, Industry)         (User, Lead, ActivityLog)
                                            │                                     │
                                            └──────────────────┬──────────────────┘
                                                               │
                                                               ▼
                                                [ SQLite Persistent Database ]
                                                (/app/data/crm.db with WAL Mode)
```

---

## 3. Technology Stack

- **Language & Runtime**: Python 3.12
- **Web Framework**: FastAPI (v0.110+)
- **ASGI Server**: Uvicorn
- **ORM & Data Layer**: SQLAlchemy 2.0 with SQLite (WAL mode, foreign key enforcement)
- **Data Validation & Settings**: Pydantic v2 & `pydantic-settings`
- **Authentication & Cryptography**: BCrypt (`passlib[bcrypt]`), HMAC-SHA256, Python-Jose (JWT)
- **Web UI & Templating**: Jinja2 templates, Semantic CSS3 Dark Glass Design System (`styles.css`), Vanilla JavaScript progressive enhancement (`crm.js`) — zero npm/Node build dependencies
- **Containerization**: Multi-stage Docker build utilizing Google Distroless non-root base (`gcr.io/distroless/cc-debian12:nonroot`)
- **CI/CD Pipeline**: Automated 9-stage Jenkins pipeline for ARM64 container compilation, Trivy scanning, Docker Hub publishing, and OCI host deployment
- **Edge Routing & Ingress**: Cloudflare Zero Trust Tunnel (`cloudflared`) with WAF and HTTPS termination
- **Testing Framework**: Pytest with SQLite in-memory fixtures (`StaticPool`), HTTPX test client — **136 automated tests (100% passing)**

---

## 4. Application Structure

```text
Portfolio_02/
├── app/
│   ├── __init__.py
│   ├── config.py                 # Pydantic Settings configuration & env validation
│   ├── database.py               # SQLAlchemy engine, session maker, DB dependency
│   ├── dependencies.py           # Auth, RBAC, CSRF, cookie & return-URL validators
│   ├── main.py                   # FastAPI app entrypoint, CORS, exception handlers
│   ├── models.py                 # SQLAlchemy ORM models (User, Lead, ActivityLog)
│   ├── schemas.py                # Pydantic request/response validation schemas
│   ├── seed.py                   # Safe synthetic demonstration data seeder
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py               # Programmatic REST authentication endpoints
│   │   ├── leads.py              # Programmatic REST lead management endpoints
│   │   └── web.py                # Server-rendered Web UI / MVC routes
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py       # Password hashing, JWT token lifecycle
│   │   ├── lead_service.py       # Lead business logic, metrics & activities
│   │   └── scoring_engine.py     # Deterministic qualification scoring engine
│   ├── static/
│   │   ├── css/
│   │   │   └── styles.css        # Dark Glass design system & responsive layout
│   │   └── js/
│   │       └── crm.js            # Progressive UI enhancements & submit protection
│   └── templates/
│       ├── base.html             # Master layout, navigation bar, role badge, footer
│       ├── dashboard.html        # Executive KPI dashboard & pipeline analytics
│       ├── auth/
│       │   └── login.html        # Glassmorphism authentication login view
│       └── leads/
│           ├── form.html         # Lead creation form workspace
│           └── list.html         # Leads pipeline workspace & filtering directory
├── tests/
│   ├── conftest.py               # Isolated in-memory fixtures & authenticated clients
│   ├── test_auth.py              # REST authentication & password hashing tests
│   ├── test_config.py            # Environment configuration & secret leak tests
│   ├── test_health.py            # Health check & uptime verification tests
│   ├── test_leads.py             # REST lead CRUD, pagination, sorting & CSV tests
│   ├── test_scoring.py           # Scoring engine algorithm unit tests
│   ├── test_security.py          # SQL injection, path traversal & CORS tests
│   ├── test_web_auth.py          # Web login, logout, cookie & CSRF tests
│   ├── test_web_dashboard.py     # Web dashboard KPI metrics & UI tests
│   ├── test_web_leads.py         # Leads workspace search, filter & export tests
│   └── test_web_leads_creation.py# Lead creation workflow, validation & XSS tests
├── .env.example                  # Environment configuration template
├── .gitignore                    # Git exclusion rules
├── .gitleaksignore               # Secret scanner rules
├── Dockerfile                    # Multi-stage Distroless ARM64 build manifest
├── docker-compose.yml            # Container service orchestration
├── Jenkinsfile                   # 9-stage CI/CD production deployment pipeline
├── LICENSE                       # Open-source MIT License
├── pyproject.toml                # Build configuration & Pytest settings
├── README.md                     # Authoritative system documentation
├── requirements-runtime.txt      # Production runtime dependency manifest
└── requirements.txt              # Complete dependency manifest
```

---

## 5. Web UI Capabilities

The Web UI delivers a dark-glass CRM workspace with real-time feedback, responsive mobile layouts, and zero external JavaScript libraries.

```text
Implemented Web UI Surface:
├── /               -> Smart Landing (Redirects authenticated to /dashboard, unauthenticated to /login)
├── /login          -> Glass Login Interface (CSRF protection, secure cookie auth, safe return URL)
├── /logout         -> Session Termination (POST route, CSRF validated, cookie destruction)
├── /dashboard      -> Executive CRM Dashboard (KPI metric cards, distribution charts, recent leads)
├── /leads          -> Leads Workspace (Search, status/industry/score filters, dynamic sorting, CSV)
└── /leads/new      -> Lead Creation Workflow (Contact & company inputs, Pydantic validation, auto-scoring)
```

> [!NOTE]
> **Implemented vs. Deferred Web UI Scope**: The browser interface currently implements user authentication (`/login`, `/logout`), executive pipeline analytics (`/dashboard`), the leads directory workspace (`/leads`), and the lead creation workflow (`/leads/new`). Individual lead detail viewing (`/leads/{id}`), in-browser activity logging, and lead editing workflows are scheduled for Phase 2E-3 and Phase 2E-4 (and remain fully accessible programmatically via the REST API).

### 1. Executive CRM Dashboard (`GET /dashboard`)
- **Key Metric Indicators (KPIs)**:
  - **Total Leads**: Total count of pipeline opportunities.
  - **Qualified / Unqualified Leads**: Instant segmentation of active prospects.
  - **Total Pipeline Value**: Aggregate annual revenue calculated across all active accounts.
  - **Average Qualification Score**: Mean qualification score across the entire pipeline.
- **Pipeline Status Distribution**: Visual breakdown of leads across all lifecycle stages.
- **Priority Classification**: Categorical distribution of `Urgent`, `High`, `Medium`, and `Low` accounts.
- **Recent Leads Feed**: Quick-access listing of the 5 most recently created opportunities.

### 2. Leads Workspace (`GET /leads`)
- **Multi-Field Partial Substring Search**: Real-time filtering matching across `first_name`, `last_name`, `email`, and `company_name`.
- **Integrated Filter Toolbar**:
  - **Status Filter**: Exact match dropdown across all `LeadStatus` values.
  - **Industry Filter**: Case-insensitive partial matching on industry domains.
  - **Minimum Score Filter**: Numerical threshold filtering (`qualification_score >= min_score`).
- **Dynamic Sorting**: Sorting on `created_at`, `qualification_score`, `annual_revenue`, and `company_size` with ascending/descending toggles.
- **Pagination**: Configurable page sizes with automatic filter-parameter preservation.
- **Responsive Dual Presentation**: Desktop table view with status/priority badges and mobile-adaptive cards below $768\text{px}$.
- **Quick CSV Export Link**: Direct export trigger streaming authoritative CSV data.
- **Action Header**: One-click navigation to the Lead Creation Workflow.

### 3. Lead Creation Workflow (`GET /leads/new`, `POST /leads/new`)
- **Sectioned Workspace**:
  - **Contact Information**: First Name (`required`), Last Name (`required`), Email (`required`), Phone, Job Title.
  - **Company & Industry Profile**: Company Name (`required`), Industry (default `"Technology"`), Company Size (default `10`), Annual Revenue (default `$50,000.00`).
  - **Ownership & Notes**: Assigned Owner (default `"Unassigned"`), Qualification Notes.
- **Server-Controlled Integrity**: Priority, qualification score, and initial status (`New`) are strictly computed server-side and excluded from client form inputs.
- **Validation Resilience**: Re-renders with HTTP `422` on validation errors, highlights invalid inputs via `.form-control-invalid` and `aria-invalid="true"`, links deterministic error messages via `aria-describedby`, and preserves all user-submitted values.
- **Post-Creation Flow**: Successful creation executes `LeadService.create_lead()`, computes score/priority, records an initial `ActivityLog`, and redirects with HTTP `303` to `/leads`.

---

## 6. REST API Reference

The REST API serves programmatic integrations and microservices. Complete interactive Swagger documentation is available at `/docs` (or OpenAPI JSON at `/openapi.json`).

| HTTP Method | Route | Description | Auth Required | Minimum Role |
|---|---|---|---|---|
| `POST` | `/api/v1/auth/register` | Register new user account | Yes | `Admin` |
| `POST` | `/api/v1/auth/login` | Authenticate user credentials & issue session | No | Public |
| `POST` | `/api/v1/auth/logout` | Terminate session & clear cookie | Yes | Any Active User |
| `GET` | `/api/v1/auth/me` | Fetch authenticated user profile | Yes | Any Active User |
| `POST` | `/api/v1/leads` | Ingest lead with automated scoring & activity logging | Yes | Any Active User |
| `GET` | `/api/v1/leads` | Paginated lead listing with search, filtering & sorting | Yes | Any Active User |
| `GET` | `/api/v1/leads/export/csv`| Stream sanitized CSV pipeline report | Yes | Any Active User |
| `GET` | `/api/v1/leads/{id}` | Retrieve lead details and activity audit history | Yes | Any Active User |
| `PUT` | `/api/v1/leads/{id}` | Update lead fields, recalculate score & log changes | Yes | Any Active User |
| `DELETE` | `/api/v1/leads/{id}` | Delete lead and associated activities | Yes | `Admin` / `Manager` |
| `GET` | `/api/v1/leads/{id}/score-breakdown` | Get itemized 4-factor scoring breakdown | Yes | Any Active User |
| `POST` | `/api/v1/leads/{id}/activities` | Append custom activity entry (Call, Meeting, Note, Email) | Yes | Any Active User |
| `GET` | `/health` | Service uptime and database connectivity probe | No | Public |

---

## 7. Qualification Scoring Engine

Lead qualification is calculated deterministically by [`app/services/scoring_engine.py`](app/services/scoring_engine.py) upon creation and whenever key attributes are updated.

```text
Total Score = Annual Revenue (30 pts) + Company Size (25 pts) + Job Title (25 pts) + Industry Match (20 pts)
```

| Factor | Criteria | Assigned Points |
|---|---|---|
| **1. Annual Revenue** (Max 30 pts) | $\ge \$1,000,000$<br/>$\ge \$250,000$<br/>$\ge \$50,000$<br/>$< \$50,000$ | 30 pts<br/>20 pts<br/>10 pts<br/>5 pts |
| **2. Company Size** (Max 25 pts) | $\ge 500\text{ employees}$<br/>$\ge 50\text{ employees}$<br/>$\ge 10\text{ employees}$<br/>$< 10\text{ employees}$ | 25 pts<br/>20 pts<br/>10 pts<br/>5 pts |
| **3. Title Seniority** (Max 25 pts) | C-Level / VP / President / Founder / Director<br/>Manager / Lead / Head<br/>Engineer / Analyst / Specialist<br/>Other | 25 pts<br/>15 pts<br/>10 pts<br/>5 pts |
| **4. Target Industry** (Max 20 pts) | Target: `Technology`, `Software`, `Finance`, `Healthcare`, `E-Commerce`<br/>Other Industries | 20 pts<br/>10 pts |

### Priority Thresholds:
- **Urgent**: Total Score $\ge 75$
- **High**: Total Score $50 - 74$
- **Medium**: Total Score $30 - 49$
- **Low**: Total Score $< 30$

---

## 8. Authentication & Role-Based Access Control (RBAC)

The system implements role-based access control across three user tiers:

```text
User Roles & Hierarchy:
├── Admin     -> Full access (User management, Lead creation/update/delete, Metrics, CSV Export)
├── Manager   -> Lead operations & deletion, pipeline metrics, CSV Export (No user registration)
└── Rep       -> Lead creation, lead viewing, lead editing, activity logging (No deletion)
```

| Operation | Admin | Manager | Sales Rep (`rep`) | Unauthenticated |
|---|:---:|:---:|:---:|:---:|
| User Registration (`POST /api/v1/auth/register`) | ✅ | ❌ (403) | ❌ (403) | ❌ (401) |
| Web Dashboard (`GET /dashboard`) | ✅ | ✅ | ✅ | ❌ (303 $\rightarrow$ `/login`) |
| Leads Workspace (`GET /leads`) | ✅ | ✅ | ✅ | ❌ (303 $\rightarrow$ `/login`) |
| Lead Creation (`GET /leads/new`, `POST /leads/new`)| ✅ | ✅ | ✅ | ❌ (303 $\rightarrow$ `/login`) |
| Lead Updates (`PUT /api/v1/leads/{id}`) | ✅ | ✅ | ✅ | ❌ (401) |
| Lead Deletion (`DELETE /api/v1/leads/{id}`) | ✅ | ✅ | ❌ (403) | ❌ (401) |
| CSV Data Export (`GET /api/v1/leads/export/csv`) | ✅ | ✅ | ✅ | ❌ (401) |

---

## 9. Security Architecture & Hardening

1. **Session & Cookie Security**:
   - Authentication tokens are delivered inside an `HttpOnly`, `SameSite=Lax` cookie (`crm_session`).
   - `Secure` flag is enforced automatically in production environments (`ENVIRONMENT=production` or `COOKIE_SECURE=true`).
2. **Cryptographic CSRF Defense**:
   - Form-based POST actions (`/login`, `/logout`, `/leads/new`) require an HMAC-SHA256 token generated via `generate_csrf_token(user_id)`.
   - Verified with constant-time comparison (`secrets.compare_digest`) checking expiration, nonce entropy, and subject identity binding.
3. **Open Redirect Mitigation**:
   - `is_safe_url()` rigorously validates return paths (`?next=`), blocking scheme-relative URLs (`//`), Windows backslash vectors (`/\`), control characters, and external hosts.
4. **CSV Formula Injection Sanitization**:
   - [`sanitize_csv_cell()`](app/routers/leads.py#L21-L29) scans all string fields before CSV writing, prepending a single quote (`'`) to any cell beginning with formula triggers (`=`, `+`, `-`, `@`, `\t`, `\r`, `\n`, `%`).
5. **XSS & Injection Protection**:
   - Full Jinja2 autoescaping enabled across all template variables; strict prohibition of `|safe` filters on untrusted user data.
   - SQLAlchemy ORM parameterized statements for all database queries.
6. **Non-Root Container Hardening**:
   - Distroless runtime image executes exclusively under unprivileged user `nonroot` (UID/GID `65532:65532`).
   - Zero package manager or shell utilities in the production runner container.
7. **Pipeline Secret & Vulnerability Scanning**:
   - Pre-build Gitleaks inspection blocks secret commits.
   - Pre-deployment Trivy container scanning blocks images with `HIGH` or `CRITICAL` CVE vulnerabilities.

---

## 10. CI/CD Pipeline & OCI Deployment Architecture

Automated deployment is orchestrated via a 9-stage Jenkins pipeline executing on an ARM64 Oracle Cloud Infrastructure (OCI) compute instance:

```text
[ Git Push to origin/main ]
           │
           ▼
[ Jenkins Pipeline Execution ]
   ├── Stage 1: Checkout & Extract Immutable Git SHA Tag
   ├── Stage 2: Secret Scanning (Gitleaks)
   ├── Stage 3: Test Suite & Coverage Verification (pytest)
   ├── Stage 4: Multi-Arch ARM64 Container Build (docker buildx)
   ├── Stage 5: Container Vulnerability Scanning (Trivy)
   ├── Stage 6: Docker Hub Publication (Tags: :<GIT_SHA> and :latest)
   ├── Stage 7: Atomic OCI Deployment (Docker Compose at /opt/projects/business-crm/)
   ├── Stage 8: 3-Layer Health Verification (App, Cloudflared Tunnel, Public Route)
   └── Stage 9: Targeted Disk Cleanup (Pruning dangling layers & old images)
           │
           ▼
[ Production Environment on OCI Host ]
   ├── Loopback Container Exposure: 127.0.0.1:8000
   ├── Persistent Volume Mount: crm_data -> /app/data/crm.db
   └── Cloudflare Zero Trust Tunnel -> https://crm.vaikuntrix.in
```

### 3-Layer Deployment Health Verification:
1. **Layer 1 (Application & Container Identity)**: Polls `http://127.0.0.1:8000/health` (asserting HTTP 200 and database connectivity) and confirms the running container matches the published immutable image tag.
2. **Layer 2 (Host Ingress)**: Confirms host `cloudflared` daemon is active and functioning.
3. **Layer 3 (Public Edge Route)**: Verifies `https://crm.vaikuntrix.in/health` responds over the public internet.

---

## 11. Local Development Setup

### Prerequisites
- Python 3.12+
- Git

### Quickstart Guide

```bash
# 1. Clone repository
git clone https://github.com/knight-sd007/Business_CRM_Lead_Management_System.git
cd Business_CRM_Lead_Management_System

# 2. Initialize Python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure local environment
cp .env.example .env

# 5. Seed synthetic demonstration data (Creates Admin: admin/AdminPass123!)
python -m app.seed

# 6. Start development server
uvicorn app.main:app --reload --port 8000
```

### Access Points:
- **Web CRM UI**: `http://localhost:8000/` (Sign in as `admin` / `AdminPass123!`)
- **API Swagger Documentation**: `http://localhost:8000/docs`
- **Health Check Probe**: `http://localhost:8000/health`

---

## 12. Testing & Verification

The test suite runs against an isolated in-memory SQLite database using SQLAlchemy's `StaticPool` to ensure complete test isolation with zero on-disk persistence side effects.

```bash
# Execute entire test suite (136 tests)
pytest

# Execute test suite with verbose output
pytest -v

# Run with test coverage report
pytest --cov=app --cov-report=term-missing
```

### Test Suite Distribution (136 Total Tests):
- `tests/test_auth.py` (10 tests): REST authentication, hashing, user registration, logout.
- `tests/test_config.py` (4 tests): Setting resolution, CORS JSON parsing, environment overrides.
- `tests/test_health.py` (1 test): Health check probe and database ping.
- `tests/test_leads.py` (13 tests): REST lead CRUD, scoring breakdown, CSV export, RBAC deletion.
- `tests/test_scoring.py` (4 tests): Scoring factor algorithms and point threshold tiers.
- `tests/test_security.py` (8 tests): SQL injection, path traversal, stack trace suppression, CSV formula injection.
- `tests/test_web_auth.py` (21 tests): Web login, logout, session cookie lifecycle, CSRF enforcement, open redirect blocks.
- `tests/test_web_dashboard.py` (16 tests): KPI aggregation, pipeline metrics, distribution charts, UI layout.
- `tests/test_web_leads.py` (25 tests): Leads Workspace search, multi-filters, sorting, pagination, CSV delegation, XSS escaping.
- `tests/test_web_leads_creation.py` (24 tests): Lead Creation form rendering, Pydantic validation, 422 error preservation, CSRF rejection, auto-scoring.

---

## 13. Implementation Status & Roadmap

| Component / Phase | Scope & Description | Status |
|---|---|:---:|
| **Phase 1: Backend Hardening** | Authentication, JWT sessions, RBAC, CSV sanitization, CORS hardening, SQLite WAL | ✅ **Completed** |
| **Phase 2A: Web Authentication** | Server-rendered login, session cookie management, HMAC-SHA256 CSRF protection | ✅ **Completed** |
| **Phase 2B: CRM Dashboard** | Executive KPI metric cards, status/priority analytics, recent activity feed | ✅ **Completed** |
| **Phase 2D: Glass UI Foundation** | Dark Glass design system (`styles.css`), shared layout (`base.html`), `crm.js` | ✅ **Completed** |
| **Phase 2E-1: Leads Workspace** | Search, status/industry/score filtering, sorting, pagination, CSV export link | ✅ **Completed** |
| **Phase 2E-2: Lead Creation** | `/leads/new` form workspace, Pydantic validation, server-side auto-scoring | ✅ **Completed** |
| **Phase 2E-3: Lead Detail Page** | Dedicated `/leads/{id}` timeline, activity log stream, interactive detail view | ⏳ *Planned* |
| **Phase 2E-4: Lead Edit & Status** | Dedicated lead update workflow and lifecycle status transitions | ⏳ *Planned* |
| **Phase 3: Production CI/CD** | Jenkins 9-stage pipeline, Distroless ARM64 build, OCI deployment, Cloudflare tunnel | ✅ **Completed** |

---

## 14. License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
