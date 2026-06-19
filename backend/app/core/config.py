
import os
import secrets
from pydantic_settings import BaseSettings

def _get_secret_key() -> str:
    key = os.getenv("SECRET_KEY")
    if not key:
        import logging
        logging.getLogger(__name__).warning(
            "SECRET_KEY not set — generating a random key. "
            "Set SECRET_KEY env variable for production."
        )
        key = secrets.token_hex(32)
    return key

class Settings(BaseSettings):
    PROJECT_NAME: str = "SparqAI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = _get_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./backend/test.db")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8000")
    SENTRY_DSN: str = os.getenv("SENTRY_DSN", "")
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

settings = Settings()
