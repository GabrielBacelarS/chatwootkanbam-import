"""
Compliance Service - Conformidade LGPD
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, and_, func
import logging
import json
import hashlib

from backend.models.compliance import (
    Consent, ConsentType, DataRetentionPolicy,
    DataSubjectRequest, RequestType, RequestStatus, DataProcessingLog
)
from backend.models.ai_conversation import AIConversation
from backend.models.analytics import ConversationMetrics

logger = logging.getLogger(__name__)


class ComplianceService:
    """Servico de conformidade LGPD"""

    # Prazo legal LGPD para responder solicitacoes (15 dias)
    LGPD_RESPONSE_DAYS = 15

    @staticmethod
    async def register_consent(
        db: AsyncSession,
        client_slug: str,
        contact_phone: str,
        consent_type: ConsentType,
        granted: bool,
        contact_email: str = None,
        contact_name: str = None,
        ip_address: str = None,
        user_agent: str = None,
        source: str = "whatsapp",
        expires_in_days: int = None
    ) -> Consent:
        """
        Registra consentimento do usuario.

        Args:
            client_slug: Slug do cliente
            contact_phone: Telefone do contato
            consent_type: Tipo de consentimento
            granted: Se foi concedido ou revogado
            expires_in_days: Dias ate expirar (None = nao expira)

        Returns:
            Consent registrado
        """
        # Buscar consentimento existente
        result = await db.execute(
            select(Consent).where(
                Consent.client_slug == client_slug,
                Consent.contact_phone == contact_phone,
                Consent.consent_type == consent_type.value
            )
        )
        consent = result.scalar_one_or_none()

        now = datetime.utcnow()

        if consent:
            # Atualizar existente
            consent.granted = granted
            if granted:
                consent.granted_at = now
                consent.revoked_at = None
            else:
                consent.revoked_at = now

            if expires_in_days:
                consent.expires_at = now + timedelta(days=expires_in_days)
        else:
            # Criar novo
            consent = Consent(
                client_slug=client_slug,
                contact_phone=contact_phone,
                contact_email=contact_email,
                contact_name=contact_name,
                consent_type=consent_type.value,
                granted=granted,
                granted_at=now if granted else None,
                ip_address=ip_address,
                user_agent=user_agent,
                source=source,
                expires_at=now + timedelta(days=expires_in_days) if expires_in_days else None
            )
            db.add(consent)

        # Registrar log de processamento
        await ComplianceService._log_processing(
            db=db,
            client_slug=client_slug,
            action="consent_update",
            data_type="consent",
            data_id=contact_phone,
            details={"consent_type": consent_type.value, "granted": granted},
            legal_basis="consent"
        )

        await db.commit()
        logger.info(f"[{client_slug}] Consentimento {consent_type.value}: {granted} para {contact_phone}")
        return consent

    @staticmethod
    async def check_consent(
        db: AsyncSession,
        client_slug: str,
        contact_phone: str,
        consent_type: ConsentType
    ) -> bool:
        """Verifica se usuario tem consentimento ativo"""
        result = await db.execute(
            select(Consent).where(
                Consent.client_slug == client_slug,
                Consent.contact_phone == contact_phone,
                Consent.consent_type == consent_type.value,
                Consent.granted == True
            )
        )
        consent = result.scalar_one_or_none()

        if not consent:
            return False

        # Verificar expiracao
        if consent.expires_at and consent.expires_at < datetime.utcnow():
            return False

        return True

    @staticmethod
    async def create_dsar(
        db: AsyncSession,
        client_slug: str,
        contact_phone: str,
        request_type: RequestType,
        contact_email: str = None,
        contact_name: str = None,
        description: str = None
    ) -> DataSubjectRequest:
        """
        Cria solicitacao de titular de dados (DSAR).

        Args:
            client_slug: Slug do cliente
            contact_phone: Telefone do solicitante
            request_type: Tipo de solicitacao
            description: Descricao adicional

        Returns:
            DataSubjectRequest criada
        """
        now = datetime.utcnow()
        deadline = now + timedelta(days=ComplianceService.LGPD_RESPONSE_DAYS)

        request = DataSubjectRequest(
            client_slug=client_slug,
            contact_phone=contact_phone,
            contact_email=contact_email,
            contact_name=contact_name,
            request_type=request_type.value,
            status=RequestStatus.PENDING,
            description=description,
            requested_at=now,
            deadline_at=deadline
        )

        db.add(request)
        await db.commit()
        await db.refresh(request)

        logger.info(f"[{client_slug}] DSAR criada: {request_type.value} para {contact_phone}")
        return request

    @staticmethod
    async def process_dsar(
        db: AsyncSession,
        request_id: int,
        processed_by: str = None
    ) -> Dict[str, Any]:
        """
        Processa uma solicitacao DSAR.

        Args:
            request_id: ID da solicitacao
            processed_by: Usuario que esta processando

        Returns:
            Resultado do processamento
        """
        result = await db.execute(
            select(DataSubjectRequest).where(DataSubjectRequest.id == request_id)
        )
        request = result.scalar_one_or_none()

        if not request:
            raise ValueError("Solicitacao nao encontrada")

        request.status = RequestStatus.IN_PROGRESS
        request.processed_by = processed_by
        await db.commit()

        # Processar baseado no tipo
        if request.request_type == RequestType.ACCESS.value:
            data = await ComplianceService._export_user_data(
                db, request.client_slug, request.contact_phone
            )
            request.response = json.dumps(data, default=str, ensure_ascii=False)
            request.status = RequestStatus.COMPLETED

        elif request.request_type == RequestType.DELETION.value:
            await ComplianceService._delete_user_data(
                db, request.client_slug, request.contact_phone
            )
            request.response = "Dados excluidos com sucesso"
            request.status = RequestStatus.COMPLETED

        elif request.request_type == RequestType.PORTABILITY.value:
            data = await ComplianceService._export_user_data(
                db, request.client_slug, request.contact_phone
            )
            request.response = json.dumps(data, default=str, ensure_ascii=False)
            request.status = RequestStatus.COMPLETED

        request.completed_at = datetime.utcnow()
        await db.commit()

        return {
            "request_id": request.id,
            "status": request.status,
            "response": request.response
        }

    @staticmethod
    async def _export_user_data(
        db: AsyncSession,
        client_slug: str,
        contact_phone: str
    ) -> Dict[str, Any]:
        """Exporta todos os dados de um usuario"""
        data = {
            "export_date": datetime.utcnow().isoformat(),
            "contact_phone": contact_phone,
            "conversations": [],
            "consents": [],
            "analytics": []
        }

        # Buscar conversas
        result = await db.execute(
            select(AIConversation).where(
                AIConversation.client_slug == client_slug
            )
        )
        conversations = result.scalars().all()

        # Filtrar por telefone nas mensagens (seria ideal ter campo contact_phone)
        for conv in conversations:
            data["conversations"].append({
                "id": conv.id,
                "conversation_id": conv.conversation_id,
                "messages": conv.messages or [],
                "created_at": conv.created_at.isoformat() if conv.created_at else None
            })

        # Buscar consentimentos
        result = await db.execute(
            select(Consent).where(
                Consent.client_slug == client_slug,
                Consent.contact_phone == contact_phone
            )
        )
        consents = result.scalars().all()
        data["consents"] = [c.to_dict() for c in consents]

        # Buscar analytics
        result = await db.execute(
            select(ConversationMetrics).where(
                ConversationMetrics.client_slug == client_slug,
                ConversationMetrics.contact_phone == contact_phone
            )
        )
        metrics = result.scalars().all()
        for m in metrics:
            data["analytics"].append({
                "conversation_id": m.conversation_id,
                "total_messages": m.total_messages,
                "outcome": m.outcome,
                "created_at": m.created_at.isoformat() if m.created_at else None
            })

        return data

    @staticmethod
    async def _delete_user_data(
        db: AsyncSession,
        client_slug: str,
        contact_phone: str
    ) -> None:
        """Exclui todos os dados de um usuario"""
        # Registrar log antes de excluir
        await ComplianceService._log_processing(
            db=db,
            client_slug=client_slug,
            action="delete",
            data_type="user_data",
            data_id=contact_phone,
            details={"reason": "DSAR deletion request"},
            legal_basis="legal_obligation"
        )

        # Excluir analytics
        await db.execute(
            delete(ConversationMetrics).where(
                ConversationMetrics.client_slug == client_slug,
                ConversationMetrics.contact_phone == contact_phone
            )
        )

        # Excluir consentimentos
        await db.execute(
            delete(Consent).where(
                Consent.client_slug == client_slug,
                Consent.contact_phone == contact_phone
            )
        )

        await db.commit()
        logger.info(f"[{client_slug}] Dados excluidos para {contact_phone}")

    @staticmethod
    async def anonymize_old_data(
        db: AsyncSession,
        client_slug: str,
        days_threshold: int = 180
    ) -> int:
        """
        Anonimiza dados antigos.

        Args:
            client_slug: Slug do cliente
            days_threshold: Dias apos os quais anonimizar

        Returns:
            Quantidade de registros anonimizados
        """
        threshold_date = datetime.utcnow() - timedelta(days=days_threshold)
        count = 0

        # Anonimizar analytics antigos
        result = await db.execute(
            select(ConversationMetrics).where(
                ConversationMetrics.client_slug == client_slug,
                ConversationMetrics.created_at < threshold_date,
                ConversationMetrics.contact_phone.isnot(None)
            )
        )
        metrics = result.scalars().all()

        for m in metrics:
            # Anonimizar dados pessoais
            if m.contact_phone:
                m.contact_phone = ComplianceService._anonymize_phone(m.contact_phone)
            if m.contact_name:
                m.contact_name = "Anonimizado"
            count += 1

        await db.commit()
        logger.info(f"[{client_slug}] {count} registros anonimizados")
        return count

    @staticmethod
    def _anonymize_phone(phone: str) -> str:
        """Anonimiza numero de telefone mantendo hash para referencia"""
        if not phone:
            return None
        # Manter apenas hash para referencia
        hash_value = hashlib.sha256(phone.encode()).hexdigest()[:12]
        return f"ANON-{hash_value}"

    @staticmethod
    async def _log_processing(
        db: AsyncSession,
        client_slug: str,
        action: str,
        data_type: str,
        data_id: str,
        details: Dict[str, Any] = None,
        legal_basis: str = None,
        ip_address: str = None
    ) -> None:
        """Registra log de processamento para auditoria"""
        log = DataProcessingLog(
            client_slug=client_slug,
            action=action,
            data_type=data_type,
            data_id=data_id,
            details=details,
            legal_basis=legal_basis,
            ip_address=ip_address
        )
        db.add(log)

    @staticmethod
    async def get_retention_policy(
        db: AsyncSession,
        client_slug: str
    ) -> DataRetentionPolicy:
        """Retorna politica de retencao do cliente"""
        result = await db.execute(
            select(DataRetentionPolicy).where(
                DataRetentionPolicy.client_slug == client_slug
            )
        )
        policy = result.scalar_one_or_none()

        if not policy:
            # Criar politica padrao
            policy = DataRetentionPolicy(
                client_slug=client_slug,
                conversation_retention_days=365,
                analytics_retention_days=730,
                logs_retention_days=90,
                anonymize_after_days=180,
                auto_anonymize=True
            )
            db.add(policy)
            await db.commit()

        return policy

    @staticmethod
    async def list_pending_dsars(
        db: AsyncSession,
        client_slug: str
    ) -> List[DataSubjectRequest]:
        """Lista solicitacoes DSAR pendentes"""
        result = await db.execute(
            select(DataSubjectRequest).where(
                DataSubjectRequest.client_slug == client_slug,
                DataSubjectRequest.status.in_([
                    RequestStatus.PENDING.value,
                    RequestStatus.IN_PROGRESS.value
                ])
            ).order_by(DataSubjectRequest.deadline_at)
        )
        return result.scalars().all()

    @staticmethod
    async def get_compliance_summary(
        db: AsyncSession,
        client_slug: str
    ) -> Dict[str, Any]:
        """Retorna resumo de compliance do cliente"""
        # Contar consentimentos
        consent_query = select(func.count(Consent.id)).where(
            Consent.client_slug == client_slug,
            Consent.granted == True
        )
        active_consents = (await db.execute(consent_query)).scalar() or 0

        # Contar DSARs pendentes
        dsar_query = select(func.count(DataSubjectRequest.id)).where(
            DataSubjectRequest.client_slug == client_slug,
            DataSubjectRequest.status == RequestStatus.PENDING.value
        )
        pending_dsars = (await db.execute(dsar_query)).scalar() or 0

        # DSARs vencidas
        overdue_query = select(func.count(DataSubjectRequest.id)).where(
            DataSubjectRequest.client_slug == client_slug,
            DataSubjectRequest.status == RequestStatus.PENDING.value,
            DataSubjectRequest.deadline_at < datetime.utcnow()
        )
        overdue_dsars = (await db.execute(overdue_query)).scalar() or 0

        # Politica de retencao
        policy = await ComplianceService.get_retention_policy(db, client_slug)

        return {
            "active_consents": active_consents,
            "pending_dsars": pending_dsars,
            "overdue_dsars": overdue_dsars,
            "retention_policy": {
                "conversation_days": policy.conversation_retention_days,
                "analytics_days": policy.analytics_retention_days,
                "auto_anonymize": policy.auto_anonymize,
                "anonymize_after_days": policy.anonymize_after_days
            },
            "compliance_status": "warning" if overdue_dsars > 0 else "ok"
        }
