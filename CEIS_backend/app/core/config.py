import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # CEIS_backend
ROOT_DIR = BASE_DIR.parent                               # root directory

# Pre-load .env explicitly into environment
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    load_dotenv(ROOT_DIR / ".env")
    load_dotenv()
except ImportError:
    pass

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Code Eagle Info Solution API"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:root@localhost:5432/codeeagle_db"
    )
    SECRET_KEY: str = os.getenv(
        "SECRET_KEY",
        "codeeagle_super_secret_jwt_key"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    ADMIN_EMAIL: str = "admin@codeeagle.com"
    ADMIN_PASSWORD: str = "AdminPassword123!"

    @property
    def SYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql://"):
            url = "postgresql+psycopg2://" + url[len("postgresql://"):]
        if "ssl=require" in url:
            url = url.replace("ssl=require", "sslmode=require")
        return url

    @property
    def ASYNC_DATABASE_URL(self) -> str:
        url = self.DATABASE_URL.strip()
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://"):]
        if url.startswith("postgresql+psycopg2://"):
            url = "postgresql+asyncpg://" + url[len("postgresql+psycopg2://"):]
        elif url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        elif url.startswith("sqlite:///"):
            url = "sqlite+aiosqlite:///" + url[len("sqlite:///"):]
        if "sslmode=" in url:
            url = url.replace("sslmode=", "ssl=")
        return url

    model_config = SettingsConfigDict(
        env_file=(".env", str(BASE_DIR / ".env"), str(ROOT_DIR / ".env")),
        extra="ignore"
    )

settings = Settings()
