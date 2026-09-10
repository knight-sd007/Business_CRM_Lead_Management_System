# Portfolio 02 — Phase 3B Implementation Report
**Project:** Business CRM Lead Management System (`Portfolio_02`)  
**Base Commit:** `392e7a3e062f32b41394e47634b0d9d3168eb820`  
**Reference Architecture:** Portfolio 01 (`AISupportChat`)  
**Scope:** Production CI/CD Pipeline (Docker Hub ARM64 Publication, OCI Local Deployment, 3-Layer Health Verification, and Targeted Disk Cleanup)

---

## 1. Executive Summary

Phase 3B implements the automated production deployment pipeline for `Business_CRM_Lead_Management_System` (`Portfolio_02`), aligning it with the proven reference architecture from `Portfolio_01`.

The pipeline extends the Phase 1 & 3A CI quality gates (Gitleaks, pytest, coverage, Trivy) with:
1. **Multi-Arch ARM64 Build (`buildx`)**: Produces immutable `linux/arm64` container images tagged with the 7-character Git SHA (`knightprime007/business-crm-lead-api:<GIT_SHA>`) and the mutable `:latest` tag.
2. **Automated Docker Hub Publication**: Securely logs in via Jenkins credentials (`docker-hub-credentials`) and publishes both tags upon passing Trivy HIGH/CRITICAL vulnerability scanning.
3. **Atomic OCI Deployment**: Deploys the immutable image tag to `/opt/projects/crm-api/` using Docker Compose while mounting the isolated SQLite persistent volume (`crm_data:/app/data`).
4. **3-Layer Bounded Health Verification**:
   - **Layer 1 (Internal App & Identity)**: Polls `http://127.0.0.1:8000/health` (HTTP 200) and `http://127.0.0.1:8000/docs`, and verifies that the running container image matches `${IMAGE_FULL_TAG}`.
   - **Layer 2 (Cloudflare Tunnel)**: Verifies the `cloudflared` daemon is active on the host.
   - **Layer 3 (Public Route)**: Verifies `https://crm.vaikuntrix.in/health` returns HTTP 200.
5. **Targeted OCI Disk Cleanup**: Prunes dangling layers and removes older P02 build tags while preserving `crm_data`, active containers, and the `:latest` tag.

---

## 2. Exact Files Modified

1. [`Jenkinsfile`](file:///mnt/f/Portfolios/Portfolio_02/Jenkinsfile): Fully configured with the 9-stage production CI/CD pipeline.
2. [`docs/portfolio-02-phase3b-implementation-report.md`](file:///mnt/f/Portfolios/Portfolio_02/docs/portfolio-02-phase3b-implementation-report.md): Canonical Phase 3B implementation documentation.

---

## 3. Pipeline Stages Architecture

```text
GitHub Push (main)
  │
  ├─► Stage 1: Checkout (Git commit checkout, Git SHA tag extraction)
  │
  ├─► Stage 2: Secret Scan (Gitleaks container scan)
  │
  ├─► Stage 3: Test & Coverage (Python 3.12 container, pytest 47/47 PASS, 94% cov)
  │
  ├─► Stage 4: Build ARM64 Image (docker buildx --platform linux/arm64 --load)
  │
  ├─► Stage 5: Container Security Scan (Trivy scan: 0 HIGH / 0 CRITICAL gate)
  │
  ├─► Stage 6: Push Docker Hub (docker-hub-credentials -> push <GIT_SHA> & latest)
  │
  ├─► Stage 7: Deploy OCI (cp docker-compose.yml -> docker compose pull & up -d)
  │
  ├─► Stage 8: Post-Deployment Verification
  │     ├── Layer 1: Internal 127.0.0.1:8000/health (HTTP 200) & container SHA match
  │     ├── Layer 2: cloudflared daemon active check
  │     └── Layer 3: Public https://crm.vaikuntrix.in/health (HTTP 200)
  │
  └─► Stage 9: OCI Disk Cleanup (Prune dangling images & obsolete P02 tags)
```

---

## 4. Security & Environment Configuration

### 4.1. Jenkins Credentials
- **Credential ID**: `docker-hub-credentials` (Username / Password for Docker Hub account `knightprime007`).
- Bound in pipeline using `withCredentials([usernamePassword(...)])` and passed via `docker login --password-stdin`.

### 4.2. Host Isolation & Secret Protection
- **Target OCI Directory**: `/opt/projects/crm-api/`
- **Host `.env` File**: `/opt/projects/crm-api/.env` (Permissions `chmod 600`, owned by `jenkins:jenkins` / `root:root`).
- **Required Production Environment Variables**:
  - `ENVIRONMENT=production`
  - `SECRET_KEY=<production-secret-key-min-32-chars>`
  - `DATABASE_URL=sqlite:////app/data/crm_lead_management.db`
  - `CORS_ORIGINS=https://crm.vaikuntrix.in`
  - `BOOTSTRAP_ADMIN_EMAIL=admin@vaikuntrix.in`
  - `BOOTSTRAP_ADMIN_USERNAME=admin`
  - `BOOTSTRAP_ADMIN_PASSWORD=<secure-bootstrap-admin-password>`
  - `BOOTSTRAP_ADMIN_FULL_NAME=System Administrator`

### 4.3. Data Durability Guarantee
- SQLite database is stored on the named Docker volume `crm_data` mounted at `/app/data`.
- Container updates execute rolling replacement (`docker compose pull` followed by `docker compose up -d`).
- Named volume `crm_data` is decoupled from container lifecycle and is **never** deleted or pruned during deployment or disk cleanup.

---

## 5. Rollback Procedure

If a new deployment fails runtime or public verification:
1. The previous immutable image tag remains available on Docker Hub (`knightprime007/business-crm-lead-api:<PREVIOUS_GIT_SHA>`).
2. An operator can instantly roll back on the OCI host without data loss:
   ```bash
   P02_IMAGE="knightprime007/business-crm-lead-api:<PREVIOUS_GIT_SHA>" \
   docker compose --env-file /opt/projects/crm-api/.env -f /opt/projects/crm-api/docker-compose.yml up -d
   ```
3. The database file `/app/data/crm_lead_management.db` inside volume `crm_data` remains preserved.

---

## 6. Manual Prerequisites & Infrastructure Readiness

| Prerequisite Item | Status / Action Required |
| :--- | :--- |
| **Jenkins Credential** | `docker-hub-credentials` pre-existing in Jenkins credential store. |
| **OCI Host Target Dir** | `sudo mkdir -p /opt/projects/crm-api/ && sudo chown -R jenkins:jenkins /opt/projects/crm-api/` |
| **OCI Production `.env`** | Create `/opt/projects/crm-api/.env` with `chmod 600` containing production secrets. |
| **Cloudflare Ingress Rule** | Add route in Cloudflare Tunnel for `crm.vaikuntrix.in` -> `http://127.0.0.1:8000`. |
| **Cloudflare DNS** | Ensure CNAME `crm.vaikuntrix.in` points to the active Cloudflare Tunnel target. |

---

## 7. Verification Summary

- **Local Tests**: 47/47 passing (100% pass rate).
- **Code Coverage**: 94% statement coverage.
- **Static Whitespace & Syntax**: `git diff --check` clean.
- **Execution Boundary Note**: Actual Docker Hub pushing, OCI container deployment, and Cloudflare routing will execute authoritatively in Jenkins Build #7 upon push to `origin/main`.
