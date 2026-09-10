# Portfolio 02 — Phase 3B OCI Deployment Directory Path Correction Report
**Project:** Business CRM Lead Management System (`Portfolio_02`)  
**Base Commit:** `f7adb5fbccde26f1d57a3478c1fe5a0066fc5827`  
**Scope:** Global Correction of P02 OCI Deployment Directory Path

---

## 1. Executive Summary

During Phase 3B operational discovery on the authoritative Oracle Cloud Infrastructure (OCI) host, it was established that the path `/opt/projects/crm-api/` does not exist. The actual, authoritative production directory for Portfolio 02 is:

```text
/opt/projects/business-crm/
```

This report documents the global correction across the CI/CD pipeline and repository documentation to align all deployment and configuration references with the actual OCI filesystem layout.

---

## 2. Directory Architecture Comparison

```text
Authoritative OCI Production Layout:
/opt/projects/business-crm/
├── .env                  # Production secrets configuration (chmod 600)
└── docker-compose.yml    # Service stack definition (Synchronized by Jenkins)
```

| Deployment Component | Previous Assumed Path | Corrected Authoritative Path |
| :--- | :--- | :--- |
| **OCI Deployment Directory** | `/opt/projects/crm-api/` | `/opt/projects/business-crm/` (**Corrected**) |
| **Production Environment File** | `/opt/projects/crm-api/.env` | `/opt/projects/business-crm/.env` (**Corrected**) |
| **Production Compose File** | `/opt/projects/crm-api/docker-compose.yml` | `/opt/projects/business-crm/docker-compose.yml` (**Corrected**) |

---

## 3. Exact Pipeline Execution Changes

In [`Jenkinsfile`](file:///mnt/f/Portfolios/Portfolio_02/Jenkinsfile) Stage `'Deploy OCI'`:
```groovy
stage('Deploy OCI') {
    steps {
        script {
            echo "Deploying P02 image ${IMAGE_FULL_TAG} to OCI host..."
            sh """
                if [ ! -f /opt/projects/business-crm/.env ]; then
                    echo "ERROR: Production environment file /opt/projects/business-crm/.env not found on OCI host!"
                    exit 1
                fi
                cp docker-compose.yml /opt/projects/business-crm/docker-compose.yml
                P02_IMAGE="${IMAGE_FULL_TAG}" docker compose --env-file /opt/projects/business-crm/.env -f /opt/projects/business-crm/docker-compose.yml pull
                P02_IMAGE="${IMAGE_FULL_TAG}" docker compose --env-file /opt/projects/business-crm/.env -f /opt/projects/business-crm/docker-compose.yml up -d
            """
        }
    }
}
```

---

## 4. Security & Persistence Integrity

1. **Named Volume Preservation**: Persistent SQLite storage remains anchored to Docker named volume `crm_data:/app/data`, completely isolated from host path changes.
2. **Secret Isolation**: Production secrets in `/opt/projects/business-crm/.env` are consumed at runtime without exposure in Git or Jenkins console logs.
3. **Loopback Protection**: Container ports remain bound strictly to `127.0.0.1:8000:8000`.

---

## 5. Static Verification Results

- **Global Grep Check**: Zero occurrences of `/opt/projects/crm-api/` remain in `Jenkinsfile` or active P02 deployment configurations.
- **Formatting Validation**: `git diff --check` passed cleanly with exit code 0.
- **Environment Boundary**: No Docker commands, Jenkins jobs, or OCI deployments were executed locally.
- **Publication Status**: Local commit only; no remote Git push executed.
