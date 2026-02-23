from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, Float, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from backend.core.database import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"
    __table_args__ = (
        UniqueConstraint('client_slug', 'conversation_id', name='uq_client_conversation'),
        Index('ix_ai_conversations_lookup', 'client_slug', 'conversation_id'),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"))
    conversation_id = Column(Integer, nullable=False)
    messages = Column(JSONB, default=[])
    # Mensagens pendentes aguardando processamento (para debounce)
    pending_messages = Column(JSONB, default=[])
    # Timestamp da ultima mensagem recebida (para debounce)
    last_message_at = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "conversation_id": self.conversation_id,
            "messages": self.messages or []
        }
