"""
Testes para endpoints de clientes
"""
import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Client


def unique_slug(prefix: str = "test") -> str:
    """Gera slug unico"""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_list_clients(client: AsyncClient):
    """Testa listagem de clientes"""
    response = await client.get("/api/clients")

    assert response.status_code == 200
    data = response.json()
    # A API retorna um dict com slug como chave
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_list_clients_with_data(client: AsyncClient, sample_client: Client):
    """Testa listagem de clientes inclui o cliente criado"""
    response = await client.get("/api/clients")

    assert response.status_code == 200
    data = response.json()

    # A API retorna dict com slug como chave
    assert sample_client.slug in data


@pytest.mark.asyncio
async def test_get_client(client: AsyncClient, sample_client: Client):
    """Testa busca de cliente especifico"""
    response = await client.get(f"/api/clients/{sample_client.slug}")

    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == sample_client.slug
    assert data["name"] == sample_client.name


@pytest.mark.asyncio
async def test_get_client_not_found(client: AsyncClient):
    """Testa busca de cliente inexistente"""
    response = await client.get("/api/clients/nao-existe-xyz-123")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_client(client: AsyncClient, db_session: AsyncSession):
    """Testa criacao de cliente"""
    slug = unique_slug("novo")
    payload = {
        "slug": slug,
        "name": "Novo Cliente Teste",
        "chatwoot_url": "https://chat.teste.com",
        "api_token": "token-123",
        "account_id": "1"
    }

    response = await client.post("/api/clients", json=payload)

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["slug"] == slug
    assert data["name"] == "Novo Cliente Teste"


@pytest.mark.asyncio
async def test_create_client_duplicate_slug(client: AsyncClient, sample_client: Client):
    """Testa criacao de cliente com slug duplicado"""
    payload = {
        "slug": sample_client.slug,  # Mesmo slug
        "name": "Outro Cliente",
        "chatwoot_url": "https://chat.teste.com",
        "api_token": "token-123",
        "account_id": "1"
    }

    response = await client.post("/api/clients", json=payload)

    # Deve retornar erro de conflito ou bad request
    assert response.status_code in [400, 409, 500]


@pytest.mark.asyncio
async def test_update_client(client: AsyncClient, sample_client: Client):
    """Testa atualizacao de cliente"""
    payload = {
        "name": "Nome Atualizado"
    }

    response = await client.put(f"/api/clients/{sample_client.slug}", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Nome Atualizado"


@pytest.mark.asyncio
async def test_delete_client(client: AsyncClient, sample_client: Client):
    """Testa exclusao de cliente"""
    response = await client.delete(f"/api/clients/{sample_client.slug}")

    assert response.status_code == 200

    # Verificar que foi deletado
    response = await client.get(f"/api/clients/{sample_client.slug}")
    assert response.status_code == 404
