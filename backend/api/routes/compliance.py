"""
Rotas de Compliance LGPD
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import logging

from backend.core.database import get_db
from backend.services.compliance_service import ComplianceService
from backend.models.compliance import ConsentType, RequestType

router = APIRouter()
logger = logging.getLogger(__name__)


class ConsentRequest(BaseModel):
    """Request para registrar consentimento"""
    contact_phone: str
    consent_type: str  # data_processing, marketing, analytics, ai_interaction, data_sharing
    granted: bool
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    expires_in_days: Optional[int] = None


class DSARRequest(BaseModel):
    """Request para criar solicitacao DSAR"""
    contact_phone: str
    request_type: str  # access, rectification, deletion, portability, restriction, objection
    contact_email: Optional[str] = None
    contact_name: Optional[str] = None
    description: Optional[str] = None


class RetentionPolicyUpdate(BaseModel):
    """Request para atualizar politica de retencao"""
    conversation_retention_days: Optional[int] = None
    analytics_retention_days: Optional[int] = None
    logs_retention_days: Optional[int] = None
    anonymize_after_days: Optional[int] = None
    auto_anonymize: Optional[bool] = None


@router.get("/{slug}/summary")
async def get_compliance_summary(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Retorna resumo de compliance do cliente"""
    try:
        summary = await ComplianceService.get_compliance_summary(db, slug)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === CONSENTIMENTO ===

@router.post("/{slug}/consent")
async def register_consent(
    slug: str,
    request: ConsentRequest,
    db: AsyncSession = Depends(get_db)
):
    """Registra consentimento do usuario"""
    try:
        # Validar tipo de consentimento
        try:
            consent_type = ConsentType(request.consent_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de consentimento invalido. Use: {[t.value for t in ConsentType]}"
            )

        consent = await ComplianceService.register_consent(
            db=db,
            client_slug=slug,
            contact_phone=request.contact_phone,
            consent_type=consent_type,
            granted=request.granted,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            expires_in_days=request.expires_in_days
        )

        return {
            "success": True,
            "consent": consent.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/consent/{contact_phone}")
async def check_consent(
    slug: str,
    contact_phone: str,
    consent_type: str,
    db: AsyncSession = Depends(get_db)
):
    """Verifica se usuario tem consentimento ativo"""
    try:
        try:
            ct = ConsentType(consent_type)
        except ValueError:
            raise HTTPException(status_code=400, detail="Tipo de consentimento invalido")

        has_consent = await ComplianceService.check_consent(
            db=db,
            client_slug=slug,
            contact_phone=contact_phone,
            consent_type=ct
        )

        return {
            "contact_phone": contact_phone,
            "consent_type": consent_type,
            "has_consent": has_consent
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === DSAR (Solicitacoes de Titular) ===

@router.post("/{slug}/dsar")
async def create_dsar(
    slug: str,
    request: DSARRequest,
    db: AsyncSession = Depends(get_db)
):
    """Cria solicitacao de titular de dados (DSAR)"""
    try:
        # Validar tipo de solicitacao
        try:
            request_type = RequestType(request.request_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de solicitacao invalido. Use: {[t.value for t in RequestType]}"
            )

        dsar = await ComplianceService.create_dsar(
            db=db,
            client_slug=slug,
            contact_phone=request.contact_phone,
            request_type=request_type,
            contact_email=request.contact_email,
            contact_name=request.contact_name,
            description=request.description
        )

        return {
            "success": True,
            "request": dsar.to_dict()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/dsar")
async def list_dsars(
    slug: str,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Lista solicitacoes DSAR"""
    try:
        from sqlalchemy import select
        from backend.models.compliance import DataSubjectRequest

        query = select(DataSubjectRequest).where(
            DataSubjectRequest.client_slug == slug
        )

        if status:
            query = query.where(DataSubjectRequest.status == status)

        query = query.order_by(DataSubjectRequest.created_at.desc())

        result = await db.execute(query)
        requests = result.scalars().all()

        return {
            "requests": [r.to_dict() for r in requests]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/dsar/pending")
async def list_pending_dsars(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Lista solicitacoes DSAR pendentes"""
    try:
        requests = await ComplianceService.list_pending_dsars(db, slug)

        return {
            "pending_count": len(requests),
            "requests": [r.to_dict() for r in requests]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{slug}/dsar/{request_id}/process")
async def process_dsar(
    slug: str,
    request_id: int,
    processed_by: str = Body(None, embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Processa uma solicitacao DSAR"""
    try:
        result = await ComplianceService.process_dsar(
            db=db,
            request_id=request_id,
            processed_by=processed_by
        )

        return {
            "success": True,
            **result
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === RETENCAO DE DADOS ===

@router.get("/{slug}/retention-policy")
async def get_retention_policy(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Retorna politica de retencao do cliente"""
    try:
        policy = await ComplianceService.get_retention_policy(db, slug)

        return {
            "conversation_retention_days": policy.conversation_retention_days,
            "analytics_retention_days": policy.analytics_retention_days,
            "logs_retention_days": policy.logs_retention_days,
            "anonymize_after_days": policy.anonymize_after_days,
            "auto_anonymize": policy.auto_anonymize,
            "auto_delete_on_request": policy.auto_delete_on_request,
            "deletion_delay_days": policy.deletion_delay_days
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{slug}/retention-policy")
async def update_retention_policy(
    slug: str,
    request: RetentionPolicyUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Atualiza politica de retencao"""
    try:
        policy = await ComplianceService.get_retention_policy(db, slug)

        if request.conversation_retention_days is not None:
            policy.conversation_retention_days = request.conversation_retention_days
        if request.analytics_retention_days is not None:
            policy.analytics_retention_days = request.analytics_retention_days
        if request.logs_retention_days is not None:
            policy.logs_retention_days = request.logs_retention_days
        if request.anonymize_after_days is not None:
            policy.anonymize_after_days = request.anonymize_after_days
        if request.auto_anonymize is not None:
            policy.auto_anonymize = request.auto_anonymize

        await db.commit()

        return {
            "success": True,
            "message": "Politica atualizada"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === ANONIMIZACAO ===

@router.post("/{slug}/anonymize")
async def anonymize_old_data(
    slug: str,
    days_threshold: int = Body(180, embed=True),
    db: AsyncSession = Depends(get_db)
):
    """Anonimiza dados antigos"""
    try:
        count = await ComplianceService.anonymize_old_data(
            db=db,
            client_slug=slug,
            days_threshold=days_threshold
        )

        return {
            "success": True,
            "records_anonymized": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# === EXPORTACAO DE DADOS ===

@router.get("/{slug}/export/{contact_phone}")
async def export_user_data(
    slug: str,
    contact_phone: str,
    db: AsyncSession = Depends(get_db)
):
    """Exporta todos os dados de um usuario"""
    try:
        data = await ComplianceService._export_user_data(
            db=db,
            client_slug=slug,
            contact_phone=contact_phone
        )

        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
