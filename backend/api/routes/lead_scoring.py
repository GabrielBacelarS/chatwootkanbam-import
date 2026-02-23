"""
Rotas de Lead Scoring
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import logging

from backend.core.database import get_db
from backend.models import Client

router = APIRouter()
logger = logging.getLogger(__name__)


class ScoringRules(BaseModel):
    """Regras de pontuacao"""
    product_view: int = 10
    price_inquiry: int = 15
    financing_inquiry: int = 20
    schedule_visit: int = 30
    transfer_request: int = 25
    multiple_messages: int = 5
    return_visit: int = 15


class ScoringThresholds(BaseModel):
    """Limites de classificacao"""
    cold: int = 25
    warm: int = 50
    hot: int = 75


class ScoringActions(BaseModel):
    """Acoes automaticas"""
    notify_on_hot: bool = True
    auto_transfer_hot: bool = False
    transfer_threshold: int = 80


class LeadScoringConfig(BaseModel):
    """Configuracao completa de Lead Scoring"""
    rules: ScoringRules = ScoringRules()
    thresholds: ScoringThresholds = ScoringThresholds()
    actions: ScoringActions = ScoringActions()


# Armazenamento em memoria (em producao, usar banco de dados)
lead_scoring_configs = {}


@router.get("/{slug}/config")
async def get_lead_scoring_config(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Retorna configuracao de lead scoring do cliente"""
    # Verificar se cliente existe
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    # Retornar config ou padrao
    config = lead_scoring_configs.get(slug, LeadScoringConfig())

    return {
        "rules": config.rules.model_dump(),
        "thresholds": config.thresholds.model_dump(),
        "actions": config.actions.model_dump()
    }


@router.put("/{slug}/config")
async def update_lead_scoring_config(
    slug: str,
    config: LeadScoringConfig,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza configuracao de lead scoring do cliente"""
    # Verificar se cliente existe
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    # Salvar config
    lead_scoring_configs[slug] = config

    logger.info(f"[{slug}] Lead scoring config atualizada")

    return {
        "success": True,
        "message": "Configuracao salva com sucesso",
        "rules": config.rules.model_dump(),
        "thresholds": config.thresholds.model_dump(),
        "actions": config.actions.model_dump()
    }


@router.post("/{slug}/calculate")
async def calculate_lead_score(
    slug: str,
    actions: list[str],
    db: AsyncSession = Depends(get_db)
):
    """Calcula score de um lead baseado nas acoes"""
    # Verificar se cliente existe
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado")

    # Obter config
    config = lead_scoring_configs.get(slug, LeadScoringConfig())
    rules = config.rules.model_dump()
    thresholds = config.thresholds

    # Calcular score
    score = 0
    for action in actions:
        score += rules.get(action, 0)

    # Classificar lead
    if score >= thresholds.hot:
        classification = "hot"
    elif score >= thresholds.warm:
        classification = "warm"
    else:
        classification = "cold"

    return {
        "score": score,
        "classification": classification,
        "thresholds": thresholds.model_dump()
    }
