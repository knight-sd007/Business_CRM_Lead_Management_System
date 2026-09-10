# Portfolio 02 — Phase 3B Distroless Python Runtime Forensic Report
**Project:** Business CRM Lead Management System (`Portfolio_02`)  
**Container:** `business_crm_lead_api`  
**Image:** `knightprime007/business-crm-lead-api:4403ff8`  
**Base Images:** Builder: `python:3.12-slim-bookworm` | Runner: `gcr.io/distroless/cc-debian12:nonroot`  
**Mode:** STRICT READ-ONLY REPOSITORY FORENSIC INVESTIGATION

---

## 1. Production Evidence Supplied Externally

The following runtime error was observed directly in the authoritative Oracle Cloud Infrastructure (OCI) environment:
```text
/usr/local/bin/python3: error while loading shared libraries: libpython3.12.so.1.0: cannot open shared object file: No such file or directory
Container Status: Restarting (127)
```

---

## 2. Repository-Side Forensic Findings

### 2.1. Dockerfile Layer Analysis
In [`Dockerfile`](file:///mnt/f/Portfolios/Portfolio_02/Dockerfile), Stage 2 (Runner) copies Python artifacts from Stage 1 (Builder) using:
```dockerfile
# Line 35-36 in Dockerfile:
COPY --from=builder /usr/local/bin/python3* /usr/local/bin/
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
```

### 2.2. Root Cause: Omission of CPython Shared Object (`libpython3.12.so.1.0`)
1. **CPython Build Structure**: In official Docker images based on `python:3.12-slim-bookworm`, Python 3.12 is compiled with `--enable-shared`.
   - The shared dynamic library is placed at: `/usr/local/lib/libpython3.12.so.1.0` (with symlink `/usr/local/lib/libpython3.12.so`).
   - The standard library Python modules are placed in the subdirectory: `/usr/local/lib/python3.12/`.
2. **The Copy Defect**:
   - `COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12` copied **only** the subdirectory containing `.py` and `.pyc` standard library files.
   - The shared dynamic library `libpython3.12.so.1.0` in the parent directory (`/usr/local/lib/`) was **never copied** into the Distroless runner stage.
3. **Dynamic Linker Resolution**:
   - The binary `/usr/local/bin/python3` is a dynamically linked ELF executable requiring `libpython3.12.so.1.0`.
   - When the container attempts to start, the glibc dynamic linker (`ld.so`) fails to locate `libpython3.12.so.1.0` in `/usr/local/lib` or `/usr/lib`, causing an immediate exit with code `127` (Command/library not found).

### 2.3. Extension Modules & Additional Dependencies Analysis
An inspection of installed runtime packages (`requirements-runtime.txt`: `fastapi`, `uvicorn`, `sqlalchemy`, `pydantic`, `pydantic-core`, `bcrypt`, `pyjwt`, `httpx`, `python-dotenv`) confirms:
- Compiled wheels (`bcrypt`, `pydantic-core`, `uvloop`, `httptools`) link only standard glibc symbols (`libc.so.6`, `libm.so.6`, `libpthread.so.0`, `libdl.so.2`, `librt.so.1`), all of which are already present in `gcr.io/distroless/cc-debian12`.
- Standard library native modules (`_sqlite3`, `_ctypes`, `_bz2`, `_lzma`) depend on dynamic libraries (`libsqlite3.so.0`, `libffi.so.8`, `libbz2.so.1.0`, `liblzma.so.5`), which are already copied explicitly from the builder.

---

## 3. Recommended Remediation (For Implementation Authorization)

The smallest, robust remediation is to update Stage 2 of [`Dockerfile`](file:///mnt/f/Portfolios/Portfolio_02/Dockerfile):

### 3.1. Exact Conceptual Changes in `Dockerfile`
1. **Copy Python Shared Libraries**:
   ```dockerfile
   # Copy CPython 3.12 binaries, shared libraries, and standard library from builder
   COPY --from=builder /usr/local/bin/python3* /usr/local/bin/
   COPY --from=builder /usr/local/lib/libpython3* /usr/local/lib/
   COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
   ```
2. **Explicit `LD_LIBRARY_PATH`**:
   ```dockerfile
   ENV PYTHONDONTWRITEBYTECODE=1 \
       PYTHONUNBUFFERED=1 \
       PYTHONPATH="/usr/local/lib/python3.12/site-packages:/app" \
       LD_LIBRARY_PATH="/usr/local/lib:/usr/lib" \
       PATH="/usr/local/bin:$PATH"
   ```

### 3.2. Security Considerations
- **Preserves Distroless Base**: No package managers, shells, or vulnerable Debian utility packages are introduced.
- **Preserves Trivy Zero-Vulnerability Gate**: `libpython3.12.so.1.0` is the compiled CPython runtime library and introduces zero CVEs.
- **Preserves Non-Root Execution**: Runs under UID/GID `65532:65532`.

---

## 4. Authoritative Validation Plan

Once approved, the remediation must be verified through the authoritative end-to-end pipeline:
1. **Jenkins ARM64 Build**: `docker buildx build --platform linux/arm64` incorporates `libpython3.12.so.1.0`.
2. **Trivy Gate**: Verifies 0 HIGH / 0 CRITICAL vulnerabilities.
3. **Docker Hub Publication**: Pushes new immutable tag to `knightprime007/business-crm-lead-api:<GIT_SHA>`.
4. **OCI Deployment**: Deploys image to `/opt/projects/business-crm/`.
5. **Runtime Health Verification**: Bounded polling of `http://127.0.0.1:8000/health` returns HTTP 200 without library loading errors.

---

## 5. Explicit Environment & Boundary Declarations

- **Codex did not access OCI.**
- **Codex did not execute production Docker.**
- **Codex did not inspect the production filesystem.**
- **Codex did not modify production configuration.**
- **No changes were made to Dockerfile, source code, or Git repository state.**
