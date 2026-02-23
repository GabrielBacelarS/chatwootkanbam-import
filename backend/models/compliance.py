"""
Modelos para Compliance LGPD
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from enum import Enum as PyEnum

from backend.core.database import Base


class ConsentType(str, PyEnum):
    """Tipos de consentimento"""
    DATA_PROCESSING = "data_processing"  # Processamento de dados
    MARKETING = "marketing"  # Comunicacoes de marketing
    ANALYTICS = "analytics"  # Coleta de analytics
    AI_INTERACTION = "ai_interaction"  # Interacao com IA
    DATA_SHARING = "data_sharing"  # Compartilhamento com terceiros


class RequestType(str, PyEnum):
    """Tipos de solicitacao DSAR"""
    ACCESS = "access"  # Acesso aos dados
    RECTIFICATION = "rectification"  # Correcao de dados
    DELETION = "deletion"  # Exclusao de dados
    PORTABILITY = "portability"  # Portabilidade
    RESTRICTION = "restriction"  # Restricao de processamento
    OBJECTION = "objection"  # Objecao ao processamento


class RequestStatus(str, PyEnum):
    """Status de solicitacao DSAR"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class Consent(Base):
    """Registro de consentimento do usuario"""
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), index=True)

    # Identificacao do usuario
    contact_phone = Column(String(50), index=True)
    contact_email = Column(String(255))
    contact_name = Column(String(255))

    # Consentimento
    consent_type = Column(String(50), nullable=False)  # ConsentType
    granted = Column(Boolean, default=False)

    # Metadata
    ip_address = Column(String(50))
    user_agent = Column(Text)
    source = Column(String(100))  # whatsapp, web, api

    # Datas
    granted_at = Column(DateTime(timezone=True))
    revoked_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "consent_type": self.consent_type,
            "granted": self.granted,
            "granted_at": self.granted_at.isoformat() if self.granted_at else None,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None
        }


class DataRetentionPolicy(Base):
    """Politica de retencao de dados por cliente"""
    __tablename__ = "data_retention_policies"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), unique=True, index=True)

    # Periodos de retencao (em dias)
    conversation_retention_days = Column(Integer, default=365)  # 1 ano
    analytics_retention_days = Column(Integer, default=730)  # 2 anos
    logs_retention_days = Column(Integer, default=90)  # 3 meses

    # Anonimizacao
    anonymize_after_days = Column(Integer, default=180)  # 6 meses
    auto_anonymize = Column(Boolean, default=True)

    # Exclusao
    auto_delete_on_request = Column(Boolean, default=True)
    deletion_delay_days = Column(Integer, default=30)  # Prazo para exclusao

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DataSubjectRequest(Base):
    """Solicitacao de titular de dados (DSAR)"""
    __tablename__ = "data_subject_requests"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), index=True)

    # Solicitante
    contact_phone = Column(String(50), index=True)
    contact_email = Column(String(255))
    contact_name = Column(String(255))

    # Solicitacao
    request_type = Column(String(50), nullable=False)  # RequestType
    status = Column(String(50), default=RequestStatus.PENDING)
    description = Column(Text)

    # Resposta
    response = Column(Text)
    response_file_url = Column(Text)  # URL do arquivo de exportacao

    # Datas
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    deadline_at = Column(DateTime(timezone=True))  # Prazo legal (15 dias LGPD)
    completed_at = Column(DateTime(timezone=True))

    # Auditoria
    processed_by = Column(String(255))  # Usuario que processou
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "contact_phone": self.contact_phone,
            "contact_email": self.contact_email,
            "contact_name": self.contact_name,
            "request_type": self.request_type,
            "status": self.status,
            "description": self.description,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "deadline_at": self.deadline_at.isoformat() if self.deadline_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


class DataProcessingLog(Base):
    """Log de processamento de dados para auditoria"""
    __tablename__ = "data_processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), index=True)

    # Acao
    action = Column(String(100), nullable=False)  # collect, process, share, delete, anonymize
    data_type = Column(String(100))  # conversation, contact, analytics
    data_id = Column(String(255))  # ID do dado afetado

    # Detalhes
    details = Column(JSONB)
    legal_basis = Column(String(100))  # consent, contract, legal_obligation, legitimate_interest

    # Metadata
    ip_address = Column(String(50))
    user_agent = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
