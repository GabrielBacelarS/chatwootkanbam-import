from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional
from pydantic import BaseModel
from backend.core.database import get_db
from backend.models import Client, AIConfig

router = APIRouter()


class ClientCreate(BaseModel):
    slug: str
    name: str
    chatwoot_url: str
    api_token: str
    account_id: str


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    chatwoot_url: Optional[str] = None
    api_token: Optional[str] = None
    account_id: Optional[str] = None


@router.get("")
async def list_clients(db: AsyncSession = Depends(get_db)):
    """Lista todos os clientes"""
    result = await db.execute(select(Client))
    clients = result.scalars().all()

    # Buscar status da IA para cada cliente
    ai_result = await db.execute(select(AIConfig))
    ai_configs = {ac.client_slug: ac.enabled for ac in ai_result.scalars().all()}

    clients_dict = {}
    for client in clients:
        d = client.to_dict()
        d["ai_enabled"] = ai_configs.get(client.slug, False)
        clients_dict[client.slug] = d

    return clients_dict


@router.get("/{slug}")
async def get_client(slug: str, db: AsyncSession = Depends(get_db)):
    """Obtém um cliente específico"""
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client.to_dict()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_client(data: ClientCreate, db: AsyncSession = Depends(get_db)):
    """Cria um novo cliente"""
    # Verificar se já existe
    result = await db.execute(select(Client).where(Client.slug == data.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Cliente já existe")

    client = Client(
        slug=data.slug,
        name=data.name,
        api_url=data.chatwoot_url,  # Mapeia chatwoot_url para api_url
        api_token=data.api_token,
        account_id=data.account_id
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return client.to_dict()


@router.put("/{slug}")
async def update_client(slug: str, data: ClientUpdate, db: AsyncSession = Depends(get_db)):
    """Atualiza um cliente"""
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    if data.name is not None:
        client.name = data.name
    if data.chatwoot_url is not None:
        client.api_url = data.chatwoot_url  # Mapeia chatwoot_url para api_url
    if data.api_token is not None:
        client.api_token = data.api_token
    if data.account_id is not None:
        client.account_id = data.account_id

    await db.commit()
    await db.refresh(client)
    return client.to_dict()


@router.delete("/{slug}")
async def delete_client(slug: str, db: AsyncSession = Depends(get_db)):
    """Remove um cliente"""
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    await db.execute(delete(Client).where(Client.slug == slug))
    await db.commit()
    return {"message": "Cliente removido"}
