import os
from typing import Union, List, Optional
from dotenv import load_dotenv
from pydantic import ConfigDict, field_validator, model_validator
from pydantic_settings import BaseSettings

# Load .env file into environment if present
load_dotenv()


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    APP_NAME: str = "Business CRM Lead Management API"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api/v1"
    DATABASE_URL: str = "sqlite:///./crm_lead_management.db"
    CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ]
    SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    COOKIE_NAME: str = "crm_session"
    COOKIE_SECURE: Optional[bool] = None
    COOKIE_SAMESITE: str = "lax"
    COOKIE_HTTPONLY: bool = True
    COOKIE_PATH: str = "/"


    # Environment-Driven Admin Bootstrap Configuration (Optional / Startup only)
    BOOTSTRAP_ADMIN_EMAIL: Optional[str] = None
    BOOTSTRAP_ADMIN_USERNAME: Optional[str] = None
    BOOTSTRAP_ADMIN_PASSWORD: Optional[str] = None
    BOOTSTRAP_ADMIN_FULL_NAME: str = "System Administrator"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        env = self.ENVIRONMENT.lower()
        if env == "production":
            if not self.SECRET_KEY or self.SECRET_KEY == "default_secret_key_for_dev_only" or len(self.SECRET_KEY) < 32:
                raise ValueError(
                    "Insecure or default SECRET_KEY is not permitted in production. "
                    "A strong SECRET_KEY (minimum 32 characters) must be configured."
                )
            if "*" in self.CORS_ORIGINS:
                raise ValueError("Wildcard CORS origin '*' is not permitted in production environment.")
        elif not self.SECRET_KEY or self.SECRET_KEY == "default_secret_key_for_dev_only":
            self.SECRET_KEY = "dev_insecure_secret_key_for_local_testing_only_32_chars"
        return self


settings = Settings()
