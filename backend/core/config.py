from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Closefy AI"
    version: str = "2.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 3000

    # Database (OBRIGATORIO - definir no .env)
    database_url: str

    # Redis (para rate limiting e cache)
    redis_url: str = "redis://localhost:6379/0"

    # Session (OBRIGATORIO - definir no .env)
    session_secret: str

    # Encriptacao (OBRIGATORIO para producao - gerar com Fernet.generate_key())
    encryption_key: Optional[str] = None

    # MinIO (armazenamento de arquivos)
    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: Optional[str] = None  # URL publica para presigned URLs (ex: storage.closefy.ai)
    minio_access_key: str = "closefy"
    minio_secret_key: str  # OBRIGATORIO - definir no .env
    minio_secure: bool = False

    # Admin (login unico)
    admin_email: str = "admin@closefy.ai"
    admin_password: str = "admin"
    jwt_secret: Optional[str] = None  # Se None, usa session_secret

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_requests_per_minute: int = 60
    rate_limit_webhook_per_minute: int = 100
    rate_limit_ai_per_minute: int = 30

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
