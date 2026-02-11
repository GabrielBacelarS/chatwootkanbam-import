from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Closefy Kanban Import"
    version: str = "2.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 3000

    # Database
    database_url: str = "postgresql+asyncpg://closefy:Closefy2026!!@localhost:5432/closefydb"

    # Session
    session_secret: str = "closefy-super-secret-key-2026"

    # Admin
    admin_email: str = "admin@example.com"
    admin_password: str = "admin123"

    # Redis (opcional)
    redis_url: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
