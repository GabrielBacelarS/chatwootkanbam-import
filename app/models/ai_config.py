from sqlalchemy import Column, String, Boolean, Integer, Text, Time, ARRAY, DateTime, ForeignKey, func
from app.core.database import Base


class AIConfig(Base):
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), unique=True)
    enabled = Column(Boolean, default=False)
    provider = Column(String(50), default="openai")
    api_key = Column(String(500))
    openai_key_for_whisper = Column(String(500))
    model = Column(String(100), default="gpt-4o-mini")
    system_prompt = Column(Text)
    welcome_message = Column(Text)
    transfer_keywords = Column(ARRAY(String), default=["atendente", "humano", "pessoa", "falar com alguém"])
    max_messages_before_transfer = Column(Integer, default=10)
    only_unassigned = Column(Boolean, default=True)
    split_message_at = Column(Integer, default=1000)
    split_by_paragraph = Column(Boolean, default=True)
    working_hours_start = Column(Time, default="08:00")
    working_hours_end = Column(Time, default="18:00")
    working_days = Column(ARRAY(Integer), default=[1, 2, 3, 4, 5])
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "enabled": self.enabled,
            "provider": self.provider,
            "api_key": self.api_key,
            "openai_key_for_whisper": self.openai_key_for_whisper,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "welcome_message": self.welcome_message,
            "transfer_keywords": self.transfer_keywords or [],
            "max_messages_before_transfer": self.max_messages_before_transfer,
            "only_unassigned": self.only_unassigned,
            "split_message_at": self.split_message_at,
            "split_by_paragraph": self.split_by_paragraph,
            "working_hours_start": str(self.working_hours_start) if self.working_hours_start else None,
            "working_hours_end": str(self.working_hours_end) if self.working_hours_end else None,
            "working_days": self.working_days or []
        }
