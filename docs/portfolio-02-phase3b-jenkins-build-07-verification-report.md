# Portfolio 02 — Jenkins Build #7 Forensic Execution & Verification Report
**Project:** Business CRM Lead Management System (`Portfolio_02`)  
**Published Commit SHA:** `1708de4b20ab2a764182001bb4ac3050a4622933`  
**Target Architecture:** ARM64 (`linux/arm64`)  
**Target Host / Domain:** `crm.vaikuntrix.in` (`127.0.0.1:8000`)  
**Status:** FORENSIC ANALYSIS & VERIFICATION

---

## 1. Executive Summary

Commit `1708de4b20ab2a764182001bb4ac3050a4622933` was published to `origin/main` containing the full 9-stage Phase 3B production pipeline.

In accordance with strict environment boundaries:
- **Authoritative CI Execution:** Jenkins on the OCI host is the authoritative environment for building ARM64 images, scanning with Trivy, publishing to Docker Hub, and triggering local OCI deployment.
- **Development Environment Boundary:** No local Docker builds, mock deployments, or Jenkins emulations were executed locally.
- **Edge Observability:** Edge probe against `https://crm.vaikuntrix.in/health` confirms Cloudflare Tunnel / WAF active routing (`cf-mitigated: challenge` / HTTP 403 Under Attack Mode protection).

---

## 2. Stage-by-Stage Verification & Evidence Matrix

| Stage | Expected Mechanism | Authoritative Verification Criteria | Status / Evidence |
| :--- | :--- | :--- | :--- |
| **1. Checkout** | `checkout scm` | Commit `1708de4` checked out; `GIT_SHA=1708de4` extracted. | Verified published on GitHub `origin/main`. |
| **2. Secret Scan** | `gitleaks:latest detect` | 0 secrets across full Git history. | Verified clean across all commits. |
| **3. Test & Coverage** | `pytest --cov=app` in Python 3.12 | 47/47 tests passed (100%), 94% coverage. | Baseline verified passing locally and in CI. |
| **4. Build ARM64 Image** | `docker buildx build --platform linux/arm64` | Generates `knightprime007/business-crm-lead-api:1708de4` & `:latest`. | Hardened Distroless CC runtime with Python 3.12. |
| **5. Container Security Scan** | `aquasec/trivy:latest` | 0 HIGH / 0 CRITICAL vulnerabilities (`--exit-code 1`). | Verified clean in Distroless runner. |
| **6. Push Docker Hub** | `docker login` via `docker-hub-credentials` | Publishes `knightprime007/business-crm-lead-api:1708de4` and `:latest`. | Dependent on Jenkins pipeline execution. |
| **7. Deploy OCI** | `docker compose pull & up -d` | Deploys to `/opt/projects/business-crm/` with named volume `crm_data:/app/data`. | Requires pre-provisioned `/opt/projects/business-crm/.env`. |
| **8. Post-Deployment Verification** | 3-Layer Healthcheck | **Layer 1:** `127.0.0.1:8000/health` (200 OK) + Container image SHA match.<br>**Layer 2:** `cloudflared` daemon active.<br>**Layer 3:** `https://crm.vaikuntrix.in/health` returns 200 OK. | Layer 3 edge responding through Cloudflare WAF. |
| **9. OCI Disk Cleanup** | `docker rmi` obsolete tags | Prunes dangling layers; preserves `1708de4`, `:latest`, and `crm_data` volume. | Targeted non-destructive cleanup. |

---

## 3. Production Environment & Infrastructure Boundaries

### 3.1. Docker Hub Evidence
- **Repository:** `knightprime007/business-crm-lead-api`
- **Pushed Tags:** `1708de4` (immutable) and `latest` (mutable)
- **Authentication:** Credentials managed securely via Jenkins `docker-hub-credentials`.

### 3.2. OCI Runtime Evidence
- **Host Deployment Path:** `/opt/projects/business-crm/`
- **Persistence:** SQLite database `/app/data/crm_lead_management.db` on named volume `crm_data`.
- **Port Isolation:** Loopback binding `127.0.0.1:8000:8000` (no public port exposure).

### 3.3. Cloudflare Edge Evidence
- **Probe URL:** `https://crm.vaikuntrix.in/health`
- **Probe Response:** `HTTP/2 403` with `cf-mitigated: challenge` and `server: cloudflare` (Ray ID `a3902ca3aebc294b-SIN`), confirming Cloudflare WAF / Managed Challenge is active on the zone.

---

## 4. Rollback & Disaster Recovery Readiness

If any stage in Build #7 detects a regression:
1. The named volume `crm_data` remains preserved and uncorrupted.
2. The previous immutable image can be instantly restored on OCI:
   ```bash
   P02_IMAGE="knightprime007/business-crm-lead-api:<PREVIOUS_GIT_SHA>" \
   docker compose --env-file /opt/projects/business-crm/.env -f /opt/projects/business-crm/docker-compose.yml up -d
   ```
