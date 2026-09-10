# Portfolio 02 — Phase 3B OCI Production Environment File Path Correction Report
**Project:** Business CRM Lead Management System (`Portfolio_02`)  
**Base Commit:** `1708de4b20ab2a764182001bb4ac3050a4622933`  
**Scope:** Correct Production Environment File Path for OCI Deployment

---

## 1. Executive Summary

A configuration defect was identified in the Phase 3B pipeline where the production environment file was assumed to be co-located with the deployment directory at `/opt/projects/crm-api/.env`.

The actual provisioned production environment file on the OCI host resides at:
`/opt/projects/business-crm/.env`

This correction updates `Jenkinsfile` and related documentation to decouple the environment file location from the application deployment directory while preserving all runtime persistence and loopback isolation guarantees.

---

## 2. Architecture & Path Disambiguation

```text
OCI Host Filesystem:
├── /opt/projects/crm-api/                  [Deployment & Compose Directory]
│   └── docker-compose.yml                  (Synchronized by Jenkins from workspace)
└── /opt/projects/business-crm/             [Service Environment Configuration Directory]
    └── .env                                (Existing production secrets file, chmod 600)
```

| Path Entity | Previous Incorrect Path | Corrected Production Path |
| :--- | :--- | :--- |
| **OCI Deployment Directory** | `/opt/projects/crm-api/` | `/opt/projects/crm-api/` (Unchanged) |
| **Compose File Location** | `/opt/projects/crm-api/docker-compose.yml` | `/opt/projects/crm-api/docker-compose.yml` (Unchanged) |
| **Production Environment File** | `/opt/projects/crm-api/.env` | `/opt/projects/business-crm/.env` (**Corrected**) |

---

## 3. Exact Logical Changes

In [`Jenkinsfile`](file:///mnt/f/Portfolios/Portfolio_02/Jenkinsfile) Stage `'Deploy OCI'`:
- Updated environment file existence assertion:
  ```bash
  if [ ! -f /opt/projects/business-crm/.env ]; then
      echo "ERROR: Production environment file /opt/projects/business-crm/.env not found on OCI host!"
      exit 1
  fi
  ```
- Updated Docker Compose command invocations:
  ```bash
  cp docker-compose.yml /opt/projects/crm-api/docker-compose.yml
  P02_IMAGE="${IMAGE_FULL_TAG}" docker compose --env-file /opt/projects/business-crm/.env -f /opt/projects/crm-api/docker-compose.yml pull
  P02_IMAGE="${IMAGE_FULL_TAG}" docker compose --env-file /opt/projects/business-crm/.env -f /opt/projects/crm-api/docker-compose.yml up -d
  ```

---

## 4. Secret & Security Boundary Confirmations

1. **Zero Secret Exposure**: No credentials, tokens, passwords, or `SECRET_KEY` values are present in `Jenkinsfile` or any repository files.
2. **No Repository `.env`**: No `.env` file exists in the repository or is tracked by Git.
3. **Strict Permissions**: The environment file on OCI remains at `chmod 600` under root/jenkins ownership.

---

## 5. Verification Performed

- **Static Grep & Analysis**: Verified all references to `/opt/projects/crm-api/.env` were eliminated from `Jenkinsfile` and replaced with `/opt/projects/business-crm/.env`.
- **Directory Decoupling**: Verified that `cp docker-compose.yml` and `-f /opt/projects/crm-api/docker-compose.yml` continue to target `/opt/projects/crm-api/`.
- **Whitespace & Formatting**: `git diff --check` executed with clean exit code 0.
- **Environment Boundary**: No Docker commands, Jenkins executions, or OCI deployments were performed in the local development environment.
- **Push Boundary**: No git push was performed.
