"""
Rotas de Integracoes CRM
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from backend.core.database import get_db
from backend.models.crm_config import CRMConfig
from backend.models import Client
from backend.integrations import HubSpotCRM, PipedriveCRM

router = APIRouter()
logger = logging.getLogger(__name__)


class CRMConnectRequest(BaseModel):
    """Request para conectar CRM"""
    provider: str  # hubspot, pipedrive
    api_key: str
    auto_create_contacts: bool = True
    auto_create_deals: bool = False
    sync_notes: bool = True
    sync_on_transfer: bool = True


class CRMUpdateRequest(BaseModel):
    """Request para atualizar configuracao CRM"""
    enabled: Optional[bool] = None
    auto_create_contacts: Optional[bool] = None
    auto_create_deals: Optional[bool] = None
    sync_notes: Optional[bool] = None
    sync_on_transfer: Optional[bool] = None
    default_pipeline_id: Optional[str] = None
    default_stage_id: Optional[str] = None
    converted_stage_id: Optional[str] = None
    field_mapping: Optional[dict] = None


def get_crm_client(config: CRMConfig):
    """Retorna cliente CRM apropriado baseado na configuracao"""
    if config.provider == "hubspot":
        return HubSpotCRM(api_key=config.api_key)
    elif config.provider == "pipedrive":
        return PipedriveCRM(api_key=config.api_key)
    else:
        raise ValueError(f"Provedor CRM nao suportado: {config.provider}")


@router.get("/{slug}/crm")
async def get_crm_config(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Retorna configuracao atual de CRM do cliente"""
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        return {
            "configured": False,
            "provider": None,
            "enabled": False
        }

    return {
        "configured": True,
        **config.to_dict()
    }


@router.post("/{slug}/crm/connect")
async def connect_crm(
    slug: str,
    request: CRMConnectRequest,
    db: AsyncSession = Depends(get_db)
):
    """Conecta integracao CRM"""
    # Verificar se cliente existe
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    # Validar provedor
    if request.provider not in ["hubspot", "pipedrive"]:
        raise HTTPException(status_code=400, detail="Provedor invalido. Use: hubspot ou pipedrive")

    # Testar conexao antes de salvar
    if request.provider == "hubspot":
        crm = HubSpotCRM(api_key=request.api_key)
    else:
        crm = PipedriveCRM(api_key=request.api_key)

    connected = await crm.test_connection()
    if not connected:
        raise HTTPException(status_code=400, detail="Falha ao conectar com CRM. Verifique a API key.")

    # Buscar ou criar config
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        config = CRMConfig(client_slug=slug)
        db.add(config)

    # Atualizar config
    config.provider = request.provider
    config.api_key = request.api_key
    config.enabled = True
    config.connected = True
    config.auto_create_contacts = request.auto_create_contacts
    config.auto_create_deals = request.auto_create_deals
    config.sync_notes = request.sync_notes
    config.sync_on_transfer = request.sync_on_transfer
    config.last_error = None

    await db.commit()

    logger.info(f"[{slug}] CRM conectado: {request.provider}")

    return {
        "success": True,
        "message": f"Conectado ao {request.provider.title()} com sucesso",
        **config.to_dict()
    }


@router.put("/{slug}/crm")
async def update_crm_config(
    slug: str,
    request: CRMUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza configuracao CRM"""
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="CRM nao configurado")

    # Atualizar campos
    if request.enabled is not None:
        config.enabled = request.enabled
    if request.auto_create_contacts is not None:
        config.auto_create_contacts = request.auto_create_contacts
    if request.auto_create_deals is not None:
        config.auto_create_deals = request.auto_create_deals
    if request.sync_notes is not None:
        config.sync_notes = request.sync_notes
    if request.sync_on_transfer is not None:
        config.sync_on_transfer = request.sync_on_transfer
    if request.default_pipeline_id is not None:
        config.default_pipeline_id = request.default_pipeline_id
    if request.default_stage_id is not None:
        config.default_stage_id = request.default_stage_id
    if request.converted_stage_id is not None:
        config.converted_stage_id = request.converted_stage_id
    if request.field_mapping is not None:
        config.field_mapping = request.field_mapping

    await db.commit()

    return {
        "success": True,
        **config.to_dict()
    }


@router.delete("/{slug}/crm")
async def disconnect_crm(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Desconecta integracao CRM"""
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="CRM nao configurado")

    await db.delete(config)
    await db.commit()

    logger.info(f"[{slug}] CRM desconectado")

    return {
        "success": True,
        "message": "CRM desconectado com sucesso"
    }


@router.post("/{slug}/crm/test")
async def test_crm_connection(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Testa conexao com CRM"""
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="CRM nao configurado")

    try:
        crm = get_crm_client(config)
        connected = await crm.test_connection()

        config.connected = connected
        if not connected:
            config.last_error = "Falha no teste de conexao"
        else:
            config.last_error = None

        await db.commit()

        return {
            "connected": connected,
            "provider": config.provider
        }

    except Exception as e:
        config.connected = False
        config.last_error = str(e)
        await db.commit()

        return {
            "connected": False,
            "error": str(e)
        }


@router.get("/{slug}/crm/pipelines")
async def get_crm_pipelines(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Lista pipelines disponiveis no CRM"""
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="CRM nao configurado")

    try:
        crm = get_crm_client(config)
        pipelines = await crm.get_pipelines()

        return {
            "pipelines": pipelines
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/crm/pipelines/{pipeline_id}/stages")
async def get_pipeline_stages(
    slug: str,
    pipeline_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Lista estagios de um pipeline"""
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="CRM nao configurado")

    try:
        crm = get_crm_client(config)
        stages = await crm.get_stages(pipeline_id)

        return {
            "pipeline_id": pipeline_id,
            "stages": stages
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slug}/crm/sync")
async def sync_conversation_to_crm(
    slug: str,
    phone: str = Body(...),
    name: Optional[str] = Body(None),
    conversation_summary: str = Body(...),
    products_discussed: list = Body(default=[]),
    outcome: Optional[str] = Body(None),
    lead_score: Optional[int] = Body(None),
    db: AsyncSession = Depends(get_db)
):
    """Sincroniza uma conversa com o CRM manualmente"""
    result = await db.execute(
        select(CRMConfig).where(CRMConfig.client_slug == slug)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="CRM nao configurado")

    if not config.enabled:
        raise HTTPException(status_code=400, detail="CRM esta desabilitado")

    try:
        crm = get_crm_client(config)
        result = await crm.sync_conversation(
            phone=phone,
            name=name,
            conversation_summary=conversation_summary,
            products_discussed=products_discussed,
            outcome=outcome,
            lead_score=lead_score
        )

        config.last_sync_at = datetime.utcnow()
        config.last_error = None
        await db.commit()

        logger.info(f"[{slug}] Conversa sincronizada com CRM: {result}")

        return {
            "success": True,
            **result
        }

    except Exception as e:
        config.last_error = str(e)
        await db.commit()

        logger.error(f"[{slug}] Erro ao sincronizar com CRM: {e}")
        raise HTTPException(status_code=500, detail=str(e))
