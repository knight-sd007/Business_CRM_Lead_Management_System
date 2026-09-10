# Portfolio 02 — Phase 3A Implementation Report
**Project:** Business CRM Lead Management System (`Portfolio_02`)  
**Base Commit:** `99a3a928ccfb517c09530b6071813d0b42f9124c`  
**Scope:** Runtime Persistence & Production Docker Compose Hardening (Phase 3A)

---

## 1. Executive Summary

Phase 3A addresses and resolves the runtime volume shadowing defect and establishes clean SQLite persistence separation for the Distroless container deployment:
1. **Isolated Data Persistence:** Fixed `docker-compose.yml` to mount the named volume to `- crm_data:/app/data` instead of the root working directory (`/app`), preventing volume shadowing of application source code.
2. **Distroless Runtime Directory Creation:** Updated `Dockerfile` to copy `/app/data` with ownership `--chown=65532:65532` into the final Distroless runner stage, ensuring Docker named volume permission inheritance for unprivileged `nonroot:nonroot` execution.
3. **Parameterized Deployment Manifest:** Updated `docker-compose.yml` to reference `${P02_IMAGE}` instead of local build context `build: .`, set absolute SQLite database path `${DATABASE_URL:-sqlite:////app/data/crm_lead_management.db}`, validated `CORS_ORIGINS`, and updated container healthcheck to exec-form JSON array syntax.

---

## 2. Exact Files Modified

1. [`Dockerfile`](file:///mnt/f/Portfolios/Portfolio_02/Dockerfile): Added `COPY --from=builder --chown=65532:65532 /app/data /app/data` into Stage 2.
2. [`docker-compose.yml`](file:///mnt/f/Portfolios/Portfolio_02/docker-compose.yml): Parameterized image reference, isolated persistent data volume, updated database path, and configured exec-form healthcheck.
3. [`docs/portfolio-02-phase3a-implementation-report.md`](file:///mnt/f/Portfolios/Portfolio_02/docs/portfolio-02-phase3a-implementation-report.md): Canonical Phase 3A report.

---

## 3. Architecture & Persistence Separation

```text
Container Filesystem (/app):
├── app/ (Immutable image layer, source code)
│   ├── main.py
│   ├── database.py
│   ├── config.py
│   └── ...
└── data/ (Persistent volume mount point: crm_data:/app/data)
    ├── crm_lead_management.db
    ├── crm_lead_management.db-wal
    └── crm_lead_management.db-shm
```

---

## 4. Verification & Testing

* **Pytest Suite:** 47 passed, 0 failed, 94% coverage.
* **Security & Static Formatting:** `git diff --check` clean (0 formatting/whitespace violations).
* **Gitleaks Status:** Clean (no hardcoded secrets or credential leaks).
* **Environment Limitations:**
  * Local Docker Build: NOT AVAILABLE (WSL daemon inactive).
  * OCI Host Deployment: NOT VERIFIED (Phase 3B deliverable).
  * Docker Hub Publication: NOT VERIFIED (Phase 3B deliverable).
  * Cloudflare Production Route: NOT VERIFIED (Phase 3B deliverable).
  * Production URL (`https://crm.vaikuntrix.in`): NOT VERIFIED (Phase 3B deliverable).

---

## 5. Phase 3B Status

Phase 3B (Jenkins publication/deployment stages, OCI host configuration, and Cloudflare routing) remains **NOT IMPLEMENTED** pending separate authorization.
