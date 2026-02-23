"""
Fixtures compartilhadas para testes

Requer PostgreSQL rodando. Configura via .env ou variaveis de ambiente.

Uso:
    pytest backend/tests/ -v --cov=backend --cov-report=html
"""
import pytest
import os
import uuid
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch
from dotenv import load_dotenv

# Carregar .env da raiz do projeto
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env'))

# Garantir que temos as variaveis necessarias
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL nao configurada. Configure no .env")

if not os.getenv("ENCRYPTION_KEY"):
    raise RuntimeError("ENCRYPTION_KEY nao configurada. Configure no .env")

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import delete
from sqlalchemy.pool import NullPool

from backend.core.database import Base, get_db
from backend.core.config import settings
from backend.main import app
from backend.models import Client, AIConfig, Product, ProductSchema


def get_test_database_url():
    """Retorna URL do banco para testes"""
    url = settings.database_url
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Cria sessao de banco para cada teste com engine proprio"""
    # Criar engine novo para cada teste (evita problemas de event loop)
    engine = create_async_engine(
        get_test_database_url(),
        echo=False,
        poolclass=NullPool  # Sem pool para evitar problemas com event loop
    )

    # Criar tabelas se nao existirem
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Criar sessao
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Fechar engine
    await engine.dispose()


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Cliente HTTP para testes de API"""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


# ============ HELPER FUNCTIONS ============

def unique_slug(prefix: str = "test") -> str:
    """Gera slug unico para evitar colisoes"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


# ============ FIXTURES DE DADOS ============

@pytest.fixture
async def sample_client(db_session: AsyncSession) -> Client:
    """Cria cliente de teste com slug unico"""
    slug = unique_slug()
    client_obj = Client(
        slug=slug,
        name="Cliente de Teste",
        api_url="https://chatwoot.test.com",
        api_token="test-token-12345",
        account_id="1"
    )
    db_session.add(client_obj)
    await db_session.commit()
    await db_session.refresh(client_obj)

    yield client_obj

    # Cleanup
    try:
        await db_session.execute(delete(Client).where(Client.slug == slug))
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def sample_ai_config(db_session: AsyncSession, sample_client: Client) -> AIConfig:
    """Cria configuracao de IA de teste"""
    config = AIConfig(
        client_slug=sample_client.slug,
        enabled=True,
        provider="openai",
        api_key="sk-test-key-12345",
        model="gpt-4o-mini",
        system_prompt="Voce e um assistente de vendas.",
        use_agent_mode=True
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    return config


@pytest.fixture
async def sample_schema(db_session: AsyncSession) -> ProductSchema:
    """Cria schema de produto de teste"""
    slug = unique_slug("schema")
    schema = ProductSchema(
        slug=slug,
        name="Schema de Teste",
        icon="mdi-test",
        description="Schema para testes",
        fields=[
            {"key": "brand", "label": "Marca", "type": "text"},
            {"key": "price", "label": "Preco", "type": "number"}
        ],
        is_active=True,
        is_default=False
    )
    db_session.add(schema)
    await db_session.commit()
    await db_session.refresh(schema)

    yield schema

    # Cleanup
    try:
        await db_session.execute(delete(ProductSchema).where(ProductSchema.slug == slug))
        await db_session.commit()
    except Exception:
        pass


@pytest.fixture
async def sample_product(db_session: AsyncSession, sample_client: Client) -> Product:
    """Cria produto de teste"""
    code = f"PROD-{uuid.uuid4().hex[:6].upper()}"
    product = Product(
        client_slug=sample_client.slug,
        name="Produto Teste",
        code=code,
        price=1000.00,
        description="Descricao do produto de teste",
        is_available=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


# ============ MOCKS ============

@pytest.fixture
def mock_openai():
    """Mock para chamadas OpenAI"""
    with patch("openai.AsyncOpenAI") as mock:
        client_mock = AsyncMock()
        mock.return_value = client_mock

        # Mock de chat completion
        completion = MagicMock()
        completion.choices = [MagicMock()]
        completion.choices[0].message.content = "Resposta de teste da IA"
        completion.choices[0].message.tool_calls = None
        client_mock.chat.completions.create = AsyncMock(return_value=completion)

        # Mock de embeddings
        embedding_response = MagicMock()
        embedding_response.data = [MagicMock()]
        embedding_response.data[0].embedding = [0.1] * 1536
        client_mock.embeddings.create = AsyncMock(return_value=embedding_response)

        yield client_mock


@pytest.fixture
def mock_chatwoot():
    """Mock para ChatwootService"""
    with patch("backend.services.chatwoot_service.ChatwootService") as mock:
        service = AsyncMock()
        mock.return_value = service

        service.send_message = AsyncMock(return_value={"id": 1, "content": "ok"})
        service.get_conversation = AsyncMock(return_value={"id": 1, "status": "open"})
        service.get_agents = AsyncMock(return_value=[{"id": 1, "name": "Agent"}])

        yield service


@pytest.fixture
def mock_redis():
    """Mock para Redis"""
    with patch("backend.core.rate_limiter.aioredis") as mock:
        redis = AsyncMock()
        mock.from_url = AsyncMock(return_value=redis)

        redis.incr = AsyncMock(return_value=1)
        redis.expire = AsyncMock(return_value=True)
        redis.zremrangebyscore = AsyncMock(return_value=0)
        redis.zcard = AsyncMock(return_value=1)
        redis.zadd = AsyncMock(return_value=1)

        pipeline = AsyncMock()
        pipeline.zremrangebyscore = MagicMock(return_value=pipeline)
        pipeline.zcard = MagicMock(return_value=pipeline)
        pipeline.zadd = MagicMock(return_value=pipeline)
        pipeline.expire = MagicMock(return_value=pipeline)
        pipeline.execute = AsyncMock(return_value=[0, 5, 1, True])
        redis.pipeline = MagicMock(return_value=pipeline)

        yield redis
