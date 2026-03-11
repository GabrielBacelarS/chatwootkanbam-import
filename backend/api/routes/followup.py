"""
Rotas de Follow-up Automatico
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from backend.core.database import get_db
from backend.models.ai_config import AIConfig
from backend.models.followup import FollowUpJob
from backend.services.followup_service import FollowUpService

router = APIRouter()
logger = logging.getLogger(__name__)


class FollowUpConfigUpdate(BaseModel):
    """Request para atualizar configuracao de follow-up"""
    followup_enabled: Optional[bool] = None
    followup_max_count: Optional[int] = None
    followup_delay_hours: Optional[int] = None
    followup_delay_minutes: Optional[int] = None
    followup_message_template: Optional[str] = None


@router.get("/{slug}/config")
async def get_followup_config(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Retorna configuracao de follow-up do cliente"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.client_slug == slug)
    )
    ai_config = result.scalar_one_or_none()

    if not ai_config:
        raise HTTPException(status_code=404, detail="Configuracao de IA nao encontrada")

    return {
        "followup_enabled": ai_config.followup_enabled or False,
        "followup_max_count": ai_config.followup_max_count or 3,
        "followup_delay_hours": ai_config.followup_delay_hours or 24,
        "followup_delay_minutes": ai_config.followup_delay_minutes or 0,
        "followup_message_template": ai_config.followup_message_template
    }


@router.put("/{slug}/config")
async def update_followup_config(
    slug: str,
    request: FollowUpConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza configuracao de follow-up do cliente"""
    result = await db.execute(
        select(AIConfig).where(AIConfig.client_slug == slug)
    )
    ai_config = result.scalar_one_or_none()

    if not ai_config:
        raise HTTPException(status_code=404, detail="Configuracao de IA nao encontrada")

    # Atualizar campos fornecidos
    if request.followup_enabled is not None:
        ai_config.followup_enabled = request.followup_enabled
    if request.followup_max_count is not None:
        if request.followup_max_count < 1 or request.followup_max_count > 10:
            raise HTTPException(
                status_code=400,
                detail="followup_max_count deve ser entre 1 e 10"
            )
        ai_config.followup_max_count = request.followup_max_count
    if request.followup_delay_hours is not None:
        if request.followup_delay_hours < 0 or request.followup_delay_hours > 168:
            raise HTTPException(
                status_code=400,
                detail="followup_delay_hours deve ser entre 0 e 168 (7 dias)"
            )
        ai_config.followup_delay_hours = request.followup_delay_hours
    if request.followup_delay_minutes is not None:
        if request.followup_delay_minutes < 0 or request.followup_delay_minutes > 59:
            raise HTTPException(
                status_code=400,
                detail="followup_delay_minutes deve ser entre 0 e 59"
            )
        ai_config.followup_delay_minutes = request.followup_delay_minutes
    if request.followup_message_template is not None:
        ai_config.followup_message_template = request.followup_message_template or None

    await db.commit()

    logger.info(f"[{slug}] Configuracao de follow-up atualizada")

    return {
        "success": True,
        "config": {
            "followup_enabled": ai_config.followup_enabled,
            "followup_max_count": ai_config.followup_max_count,
            "followup_delay_hours": ai_config.followup_delay_hours,
            "followup_delay_minutes": ai_config.followup_delay_minutes,
            "followup_message_template": ai_config.followup_message_template
        }
    }


@router.get("/{slug}/pending")
async def list_pending_followups(
    slug: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Lista follow-ups pendentes do cliente"""
    jobs = await FollowUpService.get_pending_followups(db, slug, limit)

    return {
        "pending": [job.to_dict() for job in jobs],
        "total": len(jobs)
    }


@router.get("/{slug}/stats")
async def get_followup_stats(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Retorna estatisticas de follow-ups do cliente"""
    stats = await FollowUpService.get_followup_stats(db, slug)
    return stats


@router.post("/{slug}/{job_id}/cancel")
async def cancel_followup(
    slug: str,
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancela um follow-up especifico"""
    result = await db.execute(
        select(FollowUpJob).where(
            FollowUpJob.id == job_id,
            FollowUpJob.client_slug == slug
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Follow-up nao encontrado")

    if job.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Follow-up nao pode ser cancelado (status: {job.status})"
        )

    job.status = "cancelled"
    job.cancelled_reason = "manually_cancelled"
    await db.commit()

    logger.info(f"[{slug}] Follow-up {job_id} cancelado manualmente")

    return {
        "success": True,
        "message": "Follow-up cancelado com sucesso"
    }


@router.post("/{slug}/conversation/{conversation_id}/cancel")
async def cancel_conversation_followups(
    slug: str,
    conversation_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Cancela todos os follow-ups pendentes de uma conversa"""
    count = await FollowUpService.cancel_pending_followups(
        db=db,
        client_slug=slug,
        conversation_id=conversation_id,
        reason="manually_cancelled"
    )

    return {
        "success": True,
        "cancelled_count": count,
        "message": f"{count} follow-up(s) cancelado(s)"
    }
