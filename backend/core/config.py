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

    # Session (OBRIGATORIO - definir no .env)
    session_secret: str

    # MinIO (armazenamento de arquivos)
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "closefy"
    minio_secret_key: str  # OBRIGATORIO - definir no .env
    minio_secure: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()
