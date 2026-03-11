"""
Modelo para jobs de follow-up automatico
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Index
from backend.core.database import Base


class FollowUpJob(Base):
    """
    Job de follow-up agendado.

    Representa uma mensagem de follow-up que sera enviada automaticamente
    quando o cliente nao responder apos um periodo configurado.
    """
    __tablename__ = "followup_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), nullable=False)
    conversation_id = Column(Integer, nullable=False, index=True)
    contact_phone = Column(String(50), nullable=True)

    # Numero do follow-up (1o, 2o, 3o, etc)
    followup_number = Column(Integer, default=1, nullable=False)

    # Quando o follow-up deve ser enviado
    scheduled_at = Column(DateTime, nullable=False, index=True)

    # Status do job: pending, sent, cancelled, failed
    status = Column(String(20), default="pending", nullable=False)

    # Quando foi enviado (se enviado)
    sent_at = Column(DateTime, nullable=True)

    # Motivo do cancelamento (se cancelado)
    cancelled_reason = Column(String(200), nullable=True)

    # Mensagem enviada (para historico)
    message_sent = Column(String(2000), nullable=True)

    # Erro (se falhou)
    error_message = Column(String(500), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Index composto para busca eficiente de jobs pendentes
    __table_args__ = (
        Index('ix_followup_jobs_pending', 'status', 'scheduled_at'),
        Index('ix_followup_jobs_conversation', 'client_slug', 'conversation_id', 'status'),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "conversation_id": self.conversation_id,
            "contact_phone": self.contact_phone,
            "followup_number": self.followup_number,
            "scheduled_at": self.scheduled_at.isoformat() if self.scheduled_at else None,
            "status": self.status,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "cancelled_reason": self.cancelled_reason,
            "message_sent": self.message_sent,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
