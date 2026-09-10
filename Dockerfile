# Stage 1: Build CPython 3.12 runtime dependencies and install production packages
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-0 \
    libffi-dev \
    libbz2-1.0 \
    liblzma5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-runtime.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements-runtime.txt

# Create runtime directory structure with nonroot (UID/GID 65532) permissions for SQLite persistence
RUN mkdir -p /app/data && chown -R 65532:65532 /app


# Stage 2: Minimal hardened Distroless C/C++ Debian 12 runtime
FROM gcr.io/distroless/cc-debian12:nonroot AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/usr/local/lib/python3.12/site-packages:/app" \
    LD_LIBRARY_PATH="/usr/local/lib:/usr/lib" \
    PATH="/usr/local/bin:$PATH"

# Copy CPython 3.12 binaries, shared libraries, and standard library from builder
COPY --from=builder /usr/local/bin/python3* /usr/local/bin/
COPY --from=builder /usr/local/lib/libpython3* /usr/local/lib/
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12

# Copy required dynamic shared libraries for SQLite, ctypes, bz2, and lzma
COPY --from=builder /usr/lib/*-linux-gnu*/libsqlite3.so.0* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu*/libffi.so.8* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu*/libbz2.so.1.0* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu*/liblzma.so.5* /usr/lib/

# Copy isolated production packages from builder
COPY --from=builder /install/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /install/bin/uvicorn /usr/local/bin/uvicorn

# Copy application source code and data directory with nonroot ownership
COPY --chown=65532:65532 app/ ./app/
COPY --from=builder --chown=65532:65532 /app/data /app/data

USER nonroot:nonroot

EXPOSE 8000

# Exec-form healthcheck without shell dependency
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["/usr/local/bin/python3", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"]

# Exec-form startup using verified CPython 3.12 interpreter
CMD ["/usr/local/bin/python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
