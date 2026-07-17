"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Immutable application settings validated at startup."""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    APP_SECRET_KEY: str
    APP_ALLOWED_ORIGINS: str = "http://localhost:3000"

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # Firebase
    FIREBASE_PROJECT_ID: str
    FIREBASE_CREDENTIALS_PATH: str = "./firebase-service-account.json"
    FIREBASE_DATABASE_URL: str = ""

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "stadiummind-iam"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SESSION_TTL_SECONDS: int = 86400
    REDIS_RATE_LIMIT_WINDOW_SECONDS: int = 60

    # Security
    BCRYPT_ROUNDS: int = 12
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 30
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_MAX_LENGTH: int = 128

    # Event Streaming
    EVENT_STREAM_MAX_EVENTS_PER_SEC: int = 100000
    EVENT_STREAM_PIPELINE_MAX_RETRIES: int = 3
    EVENT_STREAM_DLQ_ENABLED: bool = True
    EVENT_STREAM_FUSION_WINDOW_MS: int = 5000
    EVENT_STREAM_CACHE_L1_SIZE: int = 1000
    EVENT_STREAM_CACHE_L1_TTL: int = 60
    EVENT_STREAM_CACHE_L2_TTL: int = 300
    EVENT_STREAM_REPLAY_BATCH_SIZE: int = 500
    EVENT_STREAM_SNAPSHOT_INTERVAL_SEC: int = 60

    @field_validator("APP_SECRET_KEY", "JWT_SECRET_KEY")
    @classmethod
    def reject_default_secrets(cls, v: str) -> str:
        if v.startswith("CHANGE_ME"):
            raise ValueError("Secret keys must be replaced with actual values")
        return v

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.APP_ALLOWED_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings instance cached across the application lifecycle."""
    return Settings()
