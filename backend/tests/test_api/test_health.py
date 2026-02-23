"""
Testes para endpoints de saude e raiz
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Testa endpoint /health"""
    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Testa endpoint raiz /"""
    response = await client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "version" in data
    assert data["docs"] == "/docs"


@pytest.mark.asyncio
async def test_docs_available(client: AsyncClient):
    """Testa se documentacao OpenAPI esta disponivel"""
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "paths" in data
