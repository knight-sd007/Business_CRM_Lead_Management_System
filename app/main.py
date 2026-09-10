import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.routers import leads, auth

logger = logging.getLogger("crm_lead_management")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables dynamically on server startup
    Base.metadata.create_all(bind=engine)

    # Safe environment-driven bootstrap admin initialization
    if settings.BOOTSTRAP_ADMIN_EMAIL and settings.BOOTSTRAP_ADMIN_PASSWORD:
        from app.database import SessionLocal
        from app.services.auth_service import AuthService
        db = SessionLocal()
        try:
            auth_service = AuthService(db)
            username = settings.BOOTSTRAP_ADMIN_USERNAME or settings.BOOTSTRAP_ADMIN_EMAIL.split("@")[0]
            auth_service.bootstrap_admin_user(
                email=settings.BOOTSTRAP_ADMIN_EMAIL,
                username=username,
                password=settings.BOOTSTRAP_ADMIN_PASSWORD,
                full_name=settings.BOOTSTRAP_ADMIN_FULL_NAME
            )
        finally:
            db.close()
    yield



app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Enterprise REST API for Business Lead Qualification, Scoring, Activity Auditing, and Pipeline Management.",
    lifespan=lifespan
)

cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else [settings.CORS_ORIGINS]
# Disallow credentials with wildcard origins to prevent browser security rejection
allow_credentials = False if "*" in cors_origins else True

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(leads.router, prefix=settings.API_V1_PREFIX)



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred."}
    )


@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.ENVIRONMENT
    }
