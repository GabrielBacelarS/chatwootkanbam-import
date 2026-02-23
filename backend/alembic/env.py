"""
Alembic migration environment configuration.

Uso:
    alembic upgrade head      # Aplicar todas as migrations
    alembic downgrade -1      # Reverter ultima migration
    alembic revision --autogenerate -m "descricao"  # Criar nova migration
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Carregar .env (esta na raiz do projeto, um nivel acima)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

# Adicionar o diretorio raiz ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importar Base e todos os models
from backend.core.database import Base
from backend.models import (
    Client, AIConfig, AIKnowledgeFile, AIConversation,
    Product, ProductSchema, AITestCase, AITestRun, AITestResult,
    RateLimitLog, ConversationMetrics, DailyStats, ProductAnalytics,
    CRMConfig, ABTest, ABTestResultModel,
    Consent, DataRetentionPolicy, DataSubjectRequest, DataProcessingLog
)

# Alembic Config object
config = context.config

# Configurar URL do banco a partir do .env
# Converter asyncpg para psycopg2 (Alembic usa sync)
database_url = os.getenv("DATABASE_URL", "")
if "asyncpg" in database_url:
    database_url = database_url.replace("postgresql+asyncpg", "postgresql")
config.set_main_option("sqlalchemy.url", database_url)

# Setup Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData dos models para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
