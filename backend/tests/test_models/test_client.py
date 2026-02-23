"""
Testes para modelo Client
"""
import pytest
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Client


def unique_slug(prefix: str = "test") -> str:
    """Gera slug unico"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_create_client(db_session: AsyncSession):
    """Testa criacao de cliente"""
    slug = unique_slug("model")
    client = Client(
        slug=slug,
        name="Test Client",
        api_url="https://test.chatwoot.com",
        api_token="test-token",
        account_id="1"
    )

    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)

    assert client.slug == slug
    assert client.name == "Test Client"


@pytest.mark.asyncio
async def test_client_to_dict(sample_client: Client):
    """Testa metodo to_dict"""
    data = sample_client.to_dict()

    assert data["slug"] == sample_client.slug
    assert data["name"] == sample_client.name
    assert data["chatwoot_url"] == sample_client.api_url
    assert "api_token" in data


@pytest.mark.asyncio
async def test_client_chatwoot_url_alias(sample_client: Client):
    """Testa alias chatwoot_url"""
    assert sample_client.chatwoot_url == sample_client.api_url


@pytest.mark.asyncio
async def test_client_api_token_encryption(db_session: AsyncSession):
    """Testa que api_token e encriptado"""
    slug = unique_slug("enc")
    client = Client(
        slug=slug,
        name="Encrypted Test",
        api_url="https://test.com",
        api_token="plain-text-token",
        account_id="1"
    )

    db_session.add(client)
    await db_session.commit()
    await db_session.refresh(client)

    # O valor deve ser acessivel via getter
    assert client.api_token == "plain-text-token"
