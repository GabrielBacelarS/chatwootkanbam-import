from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import Optional, List
from pydantic import BaseModel
import httpx
from app.core.database import get_db
from app.models import Client, AIConfig, AIKnowledgeFile, AIConversation
from app.services import AIService, ChatwootService

router = APIRouter()


class AIConfigUpdate(BaseModel):
    enabled: Optional[bool] = None
    provider: Optional[str] = None
    api_key: Optional[str] = None
    openai_key_for_whisper: Optional[str] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    welcome_message: Optional[str] = None
    transfer_keywords: Optional[List[str]] = None
    max_messages_before_transfer: Optional[int] = None
    only_unassigned: Optional[bool] = None
    split_message_at: Optional[int] = None
    split_by_paragraph: Optional[bool] = None


class AITestRequest(BaseModel):
    message: str


class WebhookSetupRequest(BaseModel):
    webhookUrl: str


async def get_client(slug: str, db: AsyncSession) -> Client:
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return client


# ===== Configuração de IA =====

@router.get("/{slug}/ai-config")
async def get_ai_config(slug: str, db: AsyncSession = Depends(get_db)):
    """Obtém configuração de IA do cliente"""
    result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
    config = result.scalar_one_or_none()
    if config:
        return config.to_dict()
    return {
        "enabled": False,
        "provider": "openai",
        "model": "gpt-4o-mini",
        "transfer_keywords": ["atendente", "humano", "pessoa"],
        "max_messages_before_transfer": 10,
        "only_unassigned": True,
        "split_message_at": 1000,
        "split_by_paragraph": True
    }


@router.post("/{slug}/ai-config")
async def save_ai_config(slug: str, data: AIConfigUpdate, db: AsyncSession = Depends(get_db)):
    """Salva configuração de IA do cliente"""
    await get_client(slug, db)  # Verificar se cliente existe

    result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
    config = result.scalar_one_or_none()

    if config:
        # Atualizar existente
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(config, field, value)
    else:
        # Criar novo
        config = AIConfig(client_slug=slug, **data.model_dump(exclude_unset=True))
        db.add(config)

    await db.commit()
    await db.refresh(config)
    return config.to_dict()


# ===== Base de Conhecimento =====

@router.get("/{slug}/ai-knowledge")
async def list_knowledge_files(slug: str, db: AsyncSession = Depends(get_db)):
    """Lista arquivos de conhecimento"""
    result = await db.execute(
        select(AIKnowledgeFile).where(AIKnowledgeFile.client_slug == slug)
    )
    files = result.scalars().all()
    return [f.to_dict() for f in files]


@router.post("/{slug}/ai-knowledge")
async def upload_knowledge_file(
    slug: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Upload de arquivo de conhecimento"""
    await get_client(slug, db)

    content = await file.read()
    text_content = content.decode("utf-8", errors="ignore")

    knowledge_file = AIKnowledgeFile(
        client_slug=slug,
        filename=file.filename,
        original_name=file.filename,
        content=text_content,
        file_size=len(content)
    )
    db.add(knowledge_file)
    await db.commit()
    await db.refresh(knowledge_file)
    return knowledge_file.to_dict()


@router.delete("/{slug}/ai-knowledge/{file_id}")
async def delete_knowledge_file(slug: str, file_id: int, db: AsyncSession = Depends(get_db)):
    """Remove arquivo de conhecimento"""
    result = await db.execute(
        select(AIKnowledgeFile).where(
            AIKnowledgeFile.id == file_id,
            AIKnowledgeFile.client_slug == slug
        )
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    await db.delete(file)
    await db.commit()
    return {"message": "Arquivo removido"}


# ===== Teste de IA =====

@router.post("/{slug}/ai-test")
async def test_ai(slug: str, data: AITestRequest, db: AsyncSession = Depends(get_db)):
    """Testa a IA localmente sem webhook"""
    result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
    config = result.scalar_one_or_none()

    if not config or not config.enabled:
        raise HTTPException(status_code=400, detail="IA não configurada ou desabilitada")

    if not config.api_key:
        raise HTTPException(status_code=400, detail="API key não configurada")

    # Buscar base de conhecimento
    knowledge_result = await db.execute(
        select(AIKnowledgeFile).where(AIKnowledgeFile.client_slug == slug)
    )
    files = knowledge_result.scalars().all()
    knowledge_base = "\n\n".join([f.content for f in files if f.content])

    try:
        response = await AIService.generate_response(
            provider=config.provider,
            api_key=config.api_key,
            messages=[{"role": "user", "content": data.message}],
            model=config.model,
            system_prompt=config.system_prompt,
            knowledge_base=knowledge_base if knowledge_base else None
        )
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===== Setup de Webhook =====

@router.post("/{slug}/ai-setup-webhook")
async def setup_webhook(slug: str, data: WebhookSetupRequest, db: AsyncSession = Depends(get_db)):
    """Configura webhook automaticamente no Chatwoot"""
    client = await get_client(slug, db)

    chatwoot = ChatwootService(
        base_url=client.chatwoot_url,
        api_token=client.api_token,
        account_id=client.account_id
    )

    try:
        # Listar webhooks existentes
        webhooks = await chatwoot.get_webhooks()

        # Procurar webhook existente com nossa URL
        existing = None
        for wh in webhooks:
            if isinstance(wh, dict) and data.webhookUrl in wh.get("url", ""):
                existing = wh
                break

        if existing:
            # Atualizar existente
            await chatwoot.update_webhook(
                webhook_id=existing["id"],
                url=data.webhookUrl,
                subscriptions=["message_created"]
            )
            return {"success": True, "action": "updated", "webhook_id": existing["id"]}
        else:
            # Criar novo
            result = await chatwoot.create_webhook(
                url=data.webhookUrl,
                subscriptions=["message_created"]
            )
            return {"success": True, "action": "created", "webhook_id": result.get("id")}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
