"""
Testes para Analytics Service
"""
import pytest
import uuid
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.analytics_service import AnalyticsService
from backend.models.analytics import ConversationMetrics


def unique_conversation_id():
    """Gera ID de conversa unico"""
    return int(uuid.uuid4().int % 1000000000)


@pytest.mark.asyncio
async def test_estimate_cost():
    """Testa calculo de custo estimado"""
    # GPT-4o-mini: $0.15/1M input, $0.60/1M output
    cost = AnalyticsService.estimate_cost(1000, 500)

    # 1000 input tokens = $0.00015
    # 500 output tokens = $0.0003
    # Total = $0.00045
    assert cost > 0
    assert cost < 0.01  # Deve ser muito pequeno


@pytest.mark.asyncio
async def test_record_conversation_metrics(db_session: AsyncSession, sample_client):
    """Testa registro de metricas de conversa"""
    conv_id = unique_conversation_id()

    # Criar metricas
    metrics = await AnalyticsService.record_conversation_metrics(
        db=db_session,
        client_slug=sample_client.slug,
        conversation_id=conv_id,
        tokens_input=500,
        tokens_output=200,
        tools_used=["buscar_produtos", "calcular_financiamento"],
        channel="whatsapp",
        contact_phone="11999999999",
        contact_name="Cliente Teste"
    )

    assert metrics is not None
    assert metrics.conversation_id == conv_id
    assert metrics.tokens_input == 500
    assert metrics.tokens_output == 200
    assert metrics.tokens_total == 700
    assert "buscar_produtos" in metrics.tools_used
    assert metrics.channel == "whatsapp"


@pytest.mark.asyncio
async def test_update_existing_metrics(db_session: AsyncSession, sample_client):
    """Testa atualizacao de metricas existentes"""
    conv_id = unique_conversation_id()

    # Primeira chamada
    await AnalyticsService.record_conversation_metrics(
        db=db_session,
        client_slug=sample_client.slug,
        conversation_id=conv_id,
        tokens_input=100,
        tokens_output=50
    )

    # Segunda chamada - deve somar tokens
    metrics = await AnalyticsService.record_conversation_metrics(
        db=db_session,
        client_slug=sample_client.slug,
        conversation_id=conv_id,
        tokens_input=200,
        tokens_output=100,
        tools_used=["agendar_visita"]
    )

    assert metrics.tokens_input == 300  # 100 + 200
    assert metrics.tokens_output == 150  # 50 + 100
    assert metrics.tokens_total == 450
    assert "agendar_visita" in metrics.tools_used


@pytest.mark.asyncio
async def test_increment_message_count(db_session: AsyncSession, sample_client):
    """Testa incremento de contador de mensagens"""
    conv_id = unique_conversation_id()

    # Criar metricas primeiro
    await AnalyticsService.record_conversation_metrics(
        db=db_session,
        client_slug=sample_client.slug,
        conversation_id=conv_id
    )

    # Incrementar mensagem do usuario
    await AnalyticsService.increment_message_count(
        db=db_session,
        client_slug=sample_client.slug,
        conversation_id=conv_id,
        is_ai_message=False
    )

    # Incrementar mensagem da IA
    await AnalyticsService.increment_message_count(
        db=db_session,
        client_slug=sample_client.slug,
        conversation_id=conv_id,
        is_ai_message=True
    )

    # Verificar - nao temos acesso direto, mas nao deve dar erro


@pytest.mark.asyncio
async def test_get_overview(db_session: AsyncSession, sample_client):
    """Testa obtencao de visao geral"""
    # Criar algumas metricas de teste
    for i in range(5):
        metrics = ConversationMetrics(
            client_slug=sample_client.slug,
            conversation_id=unique_conversation_id(),
            started_at=datetime.utcnow(),
            total_messages=10,
            ai_messages=5,
            user_messages=5,
            tokens_input=1000,
            tokens_output=500,
            tokens_total=1500,
            estimated_cost=0.001,
            outcome="converted" if i % 2 == 0 else "transferred"
        )
        db_session.add(metrics)
    await db_session.commit()

    # Buscar overview
    overview = await AnalyticsService.get_overview(
        db=db_session,
        client_slug=sample_client.slug
    )

    assert overview is not None
    assert "conversations" in overview
    assert "tokens" in overview
    assert "costs" in overview
    assert "rates" in overview
    assert overview["conversations"]["total"] >= 5


@pytest.mark.asyncio
async def test_get_daily_metrics(db_session: AsyncSession, sample_client):
    """Testa metricas diarias"""
    # Criar metricas
    metrics = ConversationMetrics(
        client_slug=sample_client.slug,
        conversation_id=unique_conversation_id(),
        started_at=datetime.utcnow(),
        total_messages=5,
        tokens_total=1000,
        estimated_cost=0.001
    )
    db_session.add(metrics)
    await db_session.commit()

    # Buscar metricas diarias
    daily = await AnalyticsService.get_daily_metrics(
        db=db_session,
        client_slug=sample_client.slug
    )

    assert isinstance(daily, list)


@pytest.mark.asyncio
async def test_get_conversation_details(db_session: AsyncSession, sample_client):
    """Testa detalhes de conversas"""
    # Criar metricas
    for i in range(3):
        metrics = ConversationMetrics(
            client_slug=sample_client.slug,
            conversation_id=unique_conversation_id(),
            started_at=datetime.utcnow(),
            total_messages=10,
            outcome="converted"
        )
        db_session.add(metrics)
    await db_session.commit()

    # Buscar detalhes
    details = await AnalyticsService.get_conversation_details(
        db=db_session,
        client_slug=sample_client.slug,
        outcome="converted",
        limit=10
    )

    assert "total" in details
    assert "conversations" in details
    assert isinstance(details["conversations"], list)


@pytest.mark.asyncio
async def test_get_funnel_metrics(db_session: AsyncSession, sample_client):
    """Testa metricas de funil"""
    # Criar metricas com diferentes estagios
    stages = [
        {"products_shown": [1, 2], "products_interested": [], "transfer_requested": False, "outcome": None},
        {"products_shown": [1], "products_interested": [1], "transfer_requested": False, "outcome": None},
        {"products_shown": [1, 2, 3], "products_interested": [2], "transfer_requested": True, "outcome": None},
        {"products_shown": [1], "products_interested": [1], "transfer_requested": True, "outcome": "converted"},
    ]

    for i, stage in enumerate(stages):
        metrics = ConversationMetrics(
            client_slug=sample_client.slug,
            conversation_id=unique_conversation_id(),
            started_at=datetime.utcnow(),
            products_shown=stage["products_shown"],
            products_interested=stage["products_interested"],
            transfer_requested=stage["transfer_requested"],
            outcome=stage["outcome"]
        )
        db_session.add(metrics)
    await db_session.commit()

    # Buscar funil
    funnel = await AnalyticsService.get_funnel_metrics(
        db=db_session,
        client_slug=sample_client.slug
    )

    assert "funnel" in funnel
    assert len(funnel["funnel"]) == 5  # 5 estagios do funil


@pytest.mark.asyncio
async def test_export_data(db_session: AsyncSession, sample_client):
    """Testa exportacao de dados"""
    # Criar metricas
    metrics = ConversationMetrics(
        client_slug=sample_client.slug,
        conversation_id=unique_conversation_id(),
        started_at=datetime.utcnow(),
        total_messages=15,
        tokens_total=2000
    )
    db_session.add(metrics)
    await db_session.commit()

    # Exportar
    data = await AnalyticsService.export_data(
        db=db_session,
        client_slug=sample_client.slug
    )

    assert "export_date" in data
    assert "records" in data
    assert "total_records" in data
    assert data["total_records"] >= 1
