"""
Modelo para log de rate limiting
Armazena eventos de bloqueio para auditoria e analytics
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func

from backend.core.database import Base


class RateLimitLog(Base):
    """Log de eventos de rate limiting"""
    __tablename__ = "rate_limit_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug"), nullable=True, index=True)
    endpoint = Column(String(255), nullable=False)
    ip_address = Column(String(50), nullable=False)
    key = Column(String(255), nullable=False)  # Chave do rate limit (ex: webhook:slug)
    requests_count = Column(Integer, nullable=False)
    limit_value = Column(Integer, nullable=False)
    blocked = Column(Boolean, default=False)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        status = "BLOCKED" if self.blocked else "OK"
        return f"<RateLimitLog {self.key} {self.requests_count}/{self.limit_value} [{status}]>"
