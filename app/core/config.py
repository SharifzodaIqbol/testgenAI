from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "dev-secret-change-in-prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://testgen:testgen_secret@localhost:5432/testgen"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Groq LLM
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama3-70b-8192"
    GROQ_MAX_TOKENS: int = 4096
    GROQ_TEMPERATURE: float = 0.3

    # MinIO
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ROOT_USER: str = "minioadmin"
    MINIO_ROOT_PASSWORD: str = "minioadmin123"
    MINIO_BUCKET: str = "testgen-docs"
    MINIO_USE_SSL: bool = False

    # CORS (Исправлено: теперь это строка, которая не ломает запуск)
    CORS_ORIGINS: str = "*"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()