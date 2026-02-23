"""
Modelos para A/B Testing de Prompts
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.sql import func
from enum import Enum as PyEnum

from backend.core.database import Base


class ABTestStatus(str, PyEnum):
    """Status do teste A/B"""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


class ABTest(Base):
    """Teste A/B de prompts"""
    __tablename__ = "ab_tests"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), index=True)

    # Informacoes basicas
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default=ABTestStatus.DRAFT)

    # Variantes
    # Cada variante tem: id, name, prompt, traffic_percentage
    variants = Column(JSONB, default=[])
    # Exemplo:
    # [
    #   {"id": "A", "name": "Controle", "prompt": "...", "traffic_percentage": 50},
    #   {"id": "B", "name": "Variante B", "prompt": "...", "traffic_percentage": 50}
    # ]

    # Metrica de sucesso
    success_metric = Column(String(50), default="conversion_rate")
    # Opcoes: conversion_rate, transfer_rate, avg_messages, avg_sentiment

    # Configuracao
    min_sample_size = Column(Integer, default=100)  # Minimo de conversas por variante
    confidence_level = Column(Float, default=0.95)  # Nivel de confianca (95%)

    # Resultados
    winner_variant_id = Column(String(50))  # ID da variante vencedora
    is_significant = Column(Boolean, default=False)  # Se ha diferenca estatistica

    # Datas
    started_at = Column(DateTime(timezone=True))
    ended_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "variants": self.variants or [],
            "success_metric": self.success_metric,
            "min_sample_size": self.min_sample_size,
            "confidence_level": self.confidence_level,
            "winner_variant_id": self.winner_variant_id,
            "is_significant": self.is_significant,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class ABTestResult(Base):
    """Resultados individuais de cada conversa no teste A/B"""
    __tablename__ = "ab_test_results"

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("ab_tests.id", ondelete="CASCADE"), index=True)
    variant_id = Column(String(50), index=True)  # "A", "B", etc.
    conversation_id = Column(Integer, index=True)

    # Metricas
    converted = Column(Boolean, default=False)
    transferred = Column(Boolean, default=False)
    message_count = Column(Integer, default=0)
    sentiment_score = Column(Float)
    lead_score = Column(Integer)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
