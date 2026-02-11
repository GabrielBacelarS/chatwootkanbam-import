from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"))
    conversation_id = Column(Integer, nullable=False)
    messages = Column(JSONB, default=[])
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "conversation_id": self.conversation_id,
            "messages": self.messages or []
        }
