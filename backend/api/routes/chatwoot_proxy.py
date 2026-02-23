from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import httpx
from backend.core.database import get_db
from backend.core.http_client import get_http_client
from backend.models import Client

router = APIRouter()


async def get_client_by_slug(slug: str, db: AsyncSession) -> Client:
    """Helper para obter cliente pelo slug"""
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


@router.api_route("/{slug}/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def proxy_chatwoot(
    slug: str,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Proxy genérico para a API do Chatwoot"""
    client = await get_client_by_slug(slug, db)

    # Construir URL do Chatwoot
    chatwoot_url = f"{client.chatwoot_url.rstrip('/')}/api/v1/accounts/{client.account_id}/{path}"

    # Obter body se houver
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        body = await request.body()

    # Headers para o Chatwoot
    headers = {
        "api_access_token": client.api_token,
        "Content-Type": request.headers.get("Content-Type", "application/json")
    }

    # Usar cliente HTTP com pool de conexões
    http_client = get_http_client()
    try:
        response = await http_client.request(
            method=request.method,
            url=chatwoot_url,
            headers=headers,
            content=body,
            params=dict(request.query_params)
        )

        return Response(
            content=response.content,
            status_code=response.status_code,
            headers={"Content-Type": response.headers.get("Content-Type", "application/json")}
        )

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Erro ao conectar com Chatwoot: {str(e)}")


@router.get("/{slug}/profile")
async def get_profile(slug: str, db: AsyncSession = Depends(get_db)):
    """Obtém perfil do usuário autenticado"""
    client = await get_client_by_slug(slug, db)

    http_client = get_http_client()
    try:
        response = await http_client.get(
            f"{client.chatwoot_url.rstrip('/')}/api/v1/profile",
            headers={"api_access_token": client.api_token}
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail="Erro ao obter perfil")
