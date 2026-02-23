"""
Modelos para Analytics e Metricas
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Date, ForeignKey, ARRAY, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from backend.core.database import Base


class ConversationMetrics(Base):
    """Metricas detalhadas por conversa"""
    __tablename__ = "conversation_metrics"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), index=True)
    conversation_id = Column(Integer, index=True)

    # Timestamps
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    first_response_at = Column(DateTime(timezone=True))

    # Contagens
    total_messages = Column(Integer, default=0)
    ai_messages = Column(Integer, default=0)
    user_messages = Column(Integer, default=0)

    # Custos
    tokens_input = Column(Integer, default=0)
    tokens_output = Column(Integer, default=0)
    tokens_total = Column(Integer, default=0)
    estimated_cost = Column(Float, default=0.0)

    # Resultado
    outcome = Column(String(50))  # converted, transferred, abandoned, resolved
    transfer_requested = Column(Boolean, default=False)
    transfer_reason = Column(String(255))

    # Produtos
    products_shown = Column(ARRAY(Integer), default=[])
    products_interested = Column(ARRAY(Integer), default=[])

    # Qualidade
    sentiment_score = Column(Float)  # -1 a 1
    lead_score = Column(Integer)  # 0-100

    # Tools usadas
    tools_used = Column(ARRAY(String), default=[])
    tools_count = Column(Integer, default=0)

    # Metadata
    channel = Column(String(50))  # whatsapp, web, sms
    contact_phone = Column(String(50))
    contact_name = Column(String(255))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DailyStats(Base):
    """Estatisticas agregadas por dia"""
    __tablename__ = "daily_stats"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), index=True)
    date = Column(Date, index=True)

    # Conversas
    total_conversations = Column(Integer, default=0)
    new_conversations = Column(Integer, default=0)
    resolved_conversations = Column(Integer, default=0)

    # Mensagens
    total_messages = Column(Integer, default=0)
    ai_messages = Column(Integer, default=0)
    user_messages = Column(Integer, default=0)

    # Custos
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # Resultados
    conversions = Column(Integer, default=0)
    transfers = Column(Integer, default=0)
    abandoned = Column(Integer, default=0)

    # Performance
    avg_response_time_ms = Column(Float)  # Tempo medio de resposta em ms
    avg_conversation_length = Column(Float)  # Numero medio de mensagens
    avg_sentiment = Column(Float)  # Sentimento medio
    avg_lead_score = Column(Float)  # Lead score medio

    # Taxa
    conversion_rate = Column(Float)  # conversions / total_conversations
    transfer_rate = Column(Float)  # transfers / total_conversations
    resolution_rate = Column(Float)  # resolved / total_conversations

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProductAnalytics(Base):
    """Analytics por produto"""
    __tablename__ = "product_analytics"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), index=True)
    date = Column(Date, index=True)

    # Metricas
    views = Column(Integer, default=0)  # Quantas vezes foi mostrado
    interests = Column(Integer, default=0)  # Quantas vezes geraram interesse
    inquiries = Column(Integer, default=0)  # Quantas perguntas sobre ele
    conversions = Column(Integer, default=0)  # Quantas conversoes

    # Taxa
    interest_rate = Column(Float)  # interests / views
    conversion_rate = Column(Float)  # conversions / views

    created_at = Column(DateTime(timezone=True), server_default=func.now())
