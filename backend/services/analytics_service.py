"""
Analytics Service - Calculos e agregacoes de metricas
"""
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.dialects.postgresql import JSONB
import logging

from backend.models.analytics import ConversationMetrics, DailyStats, ProductAnalytics
from backend.models.ai_conversation import AIConversation
from backend.models.product import Product

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Servico para calculos e agregacoes de analytics"""

    # Custos aproximados por 1000 tokens (GPT-4o-mini)
    COST_PER_1K_INPUT = 0.00015  # $0.15 per 1M input
    COST_PER_1K_OUTPUT = 0.0006  # $0.60 per 1M output

    @staticmethod
    def estimate_cost(tokens_input: int, tokens_output: int) -> float:
        """Estima custo em USD baseado em tokens"""
        cost_input = (tokens_input / 1000) * AnalyticsService.COST_PER_1K_INPUT
        cost_output = (tokens_output / 1000) * AnalyticsService.COST_PER_1K_OUTPUT
        return round(cost_input + cost_output, 6)

    @staticmethod
    async def record_conversation_metrics(
        db: AsyncSession,
        client_slug: str,
        conversation_id: int,
        tokens_input: int = 0,
        tokens_output: int = 0,
        tools_used: List[str] = None,
        outcome: str = None,
        products_shown: List[int] = None,
        products_interested: List[int] = None,
        channel: str = "whatsapp",
        contact_phone: str = None,
        contact_name: str = None,
        transfer_requested: bool = False,
        transfer_reason: str = None
    ) -> ConversationMetrics:
        """Registra metricas de uma conversa"""

        # Verificar se ja existe metricas para essa conversa
        result = await db.execute(
            select(ConversationMetrics).where(
                ConversationMetrics.client_slug == client_slug,
                ConversationMetrics.conversation_id == conversation_id
            )
        )
        metrics = result.scalar_one_or_none()

        if not metrics:
            metrics = ConversationMetrics(
                client_slug=client_slug,
                conversation_id=conversation_id,
                started_at=datetime.utcnow(),
                channel=channel,
                contact_phone=contact_phone,
                contact_name=contact_name
            )
            db.add(metrics)

        # Atualizar metricas
        metrics.tokens_input = (metrics.tokens_input or 0) + tokens_input
        metrics.tokens_output = (metrics.tokens_output or 0) + tokens_output
        metrics.tokens_total = metrics.tokens_input + metrics.tokens_output
        metrics.estimated_cost = AnalyticsService.estimate_cost(
            metrics.tokens_input, metrics.tokens_output
        )

        if tools_used:
            existing_tools = list(metrics.tools_used or [])
            for tool in tools_used:
                if tool not in existing_tools:
                    existing_tools.append(tool)
            metrics.tools_used = existing_tools
            metrics.tools_count = len(existing_tools)

        if products_shown:
            existing = list(metrics.products_shown or [])
            for pid in products_shown:
                if pid not in existing:
                    existing.append(pid)
            metrics.products_shown = existing

        if products_interested:
            existing = list(metrics.products_interested or [])
            for pid in products_interested:
                if pid not in existing:
                    existing.append(pid)
            metrics.products_interested = existing

        if outcome:
            metrics.outcome = outcome
            metrics.ended_at = datetime.utcnow()

        if transfer_requested:
            metrics.transfer_requested = True
            metrics.transfer_reason = transfer_reason

        await db.commit()
        return metrics

    @staticmethod
    async def increment_message_count(
        db: AsyncSession,
        client_slug: str,
        conversation_id: int,
        is_ai_message: bool = False
    ) -> None:
        """Incrementa contagem de mensagens"""
        result = await db.execute(
            select(ConversationMetrics).where(
                ConversationMetrics.client_slug == client_slug,
                ConversationMetrics.conversation_id == conversation_id
            )
        )
        metrics = result.scalar_one_or_none()

        if metrics:
            metrics.total_messages = (metrics.total_messages or 0) + 1
            if is_ai_message:
                metrics.ai_messages = (metrics.ai_messages or 0) + 1
                if not metrics.first_response_at:
                    metrics.first_response_at = datetime.utcnow()
            else:
                metrics.user_messages = (metrics.user_messages or 0) + 1
            await db.commit()

    @staticmethod
    async def get_overview(
        db: AsyncSession,
        client_slug: str,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Retorna visao geral de analytics"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Total de conversas
        total_conversations_query = select(func.count(ConversationMetrics.id)).where(
            ConversationMetrics.client_slug == client_slug,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        )
        total_conversations = (await db.execute(total_conversations_query)).scalar() or 0

        # Conversas por outcome
        outcomes_query = select(
            ConversationMetrics.outcome,
            func.count(ConversationMetrics.id)
        ).where(
            ConversationMetrics.client_slug == client_slug,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        ).group_by(ConversationMetrics.outcome)
        outcomes_result = (await db.execute(outcomes_query)).all()
        outcomes = {(row[0] or 'pending'): row[1] for row in outcomes_result}

        # Totais de tokens e custos
        totals_query = select(
            func.sum(ConversationMetrics.tokens_input).label('tokens_in'),
            func.sum(ConversationMetrics.tokens_output).label('tokens_out'),
            func.sum(ConversationMetrics.tokens_total).label('tokens_total'),
            func.sum(ConversationMetrics.estimated_cost).label('total_cost'),
            func.avg(ConversationMetrics.total_messages).label('avg_messages')
        ).where(
            ConversationMetrics.client_slug == client_slug,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        )
        totals = (await db.execute(totals_query)).one()

        # Transferencias
        transfers_query = select(func.count(ConversationMetrics.id)).where(
            ConversationMetrics.client_slug == client_slug,
            ConversationMetrics.transfer_requested == True,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        )
        total_transfers = (await db.execute(transfers_query)).scalar() or 0

        # Calcular taxas
        conversion_rate = (outcomes.get('converted', 0) / total_conversations * 100) if total_conversations > 0 else 0
        transfer_rate = (total_transfers / total_conversations * 100) if total_conversations > 0 else 0

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "conversations": {
                "total": total_conversations,
                "by_outcome": outcomes,
                "average_messages": round(float(totals.avg_messages or 0), 1)
            },
            "tokens": {
                "input": int(totals.tokens_in or 0),
                "output": int(totals.tokens_out or 0),
                "total": int(totals.tokens_total or 0)
            },
            "costs": {
                "total_usd": round(float(totals.total_cost or 0), 4),
                "average_per_conversation": round(
                    float(totals.total_cost or 0) / total_conversations, 6
                ) if total_conversations > 0 else 0
            },
            "rates": {
                "conversion": round(conversion_rate, 2),
                "transfer": round(transfer_rate, 2)
            },
            "transfers": {
                "total": total_transfers
            }
        }

    @staticmethod
    async def get_daily_metrics(
        db: AsyncSession,
        client_slug: str,
        start_date: date = None,
        end_date: date = None
    ) -> List[Dict[str, Any]]:
        """Retorna metricas agregadas por dia"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Agregar por dia
        query = select(
            cast(ConversationMetrics.started_at, Date).label('date'),
            func.count(ConversationMetrics.id).label('conversations'),
            func.sum(ConversationMetrics.total_messages).label('messages'),
            func.sum(ConversationMetrics.ai_messages).label('ai_messages'),
            func.sum(ConversationMetrics.user_messages).label('user_messages'),
            func.sum(ConversationMetrics.tokens_total).label('tokens'),
            func.sum(ConversationMetrics.estimated_cost).label('cost'),
            func.count(ConversationMetrics.id).filter(
                ConversationMetrics.outcome == 'converted'
            ).label('conversions'),
            func.count(ConversationMetrics.id).filter(
                ConversationMetrics.transfer_requested == True
            ).label('transfers')
        ).where(
            ConversationMetrics.client_slug == client_slug,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        ).group_by(
            cast(ConversationMetrics.started_at, Date)
        ).order_by(
            cast(ConversationMetrics.started_at, Date)
        )

        result = await db.execute(query)
        rows = result.all()

        return [
            {
                "date": row.date.isoformat() if row.date else None,
                "conversations": row.conversations or 0,
                "messages": row.messages or 0,
                "ai_messages": row.ai_messages or 0,
                "user_messages": row.user_messages or 0,
                "tokens": row.tokens or 0,
                "cost_usd": round(float(row.cost or 0), 4),
                "conversions": row.conversions or 0,
                "transfers": row.transfers or 0,
                "conversion_rate": round(
                    (row.conversions or 0) / row.conversations * 100, 2
                ) if row.conversations else 0
            }
            for row in rows
        ]

    @staticmethod
    async def get_conversation_details(
        db: AsyncSession,
        client_slug: str,
        start_date: date = None,
        end_date: date = None,
        outcome: str = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Retorna lista detalhada de conversas"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Query base
        conditions = [
            ConversationMetrics.client_slug == client_slug,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        ]

        if outcome:
            conditions.append(ConversationMetrics.outcome == outcome)

        # Total count
        count_query = select(func.count(ConversationMetrics.id)).where(*conditions)
        total = (await db.execute(count_query)).scalar() or 0

        # Buscar conversas
        query = select(ConversationMetrics).where(
            *conditions
        ).order_by(
            ConversationMetrics.started_at.desc()
        ).limit(limit).offset(offset)

        result = await db.execute(query)
        conversations = result.scalars().all()

        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "conversations": [
                {
                    "id": c.id,
                    "conversation_id": c.conversation_id,
                    "started_at": c.started_at.isoformat() if c.started_at else None,
                    "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                    "outcome": c.outcome,
                    "total_messages": c.total_messages,
                    "ai_messages": c.ai_messages,
                    "user_messages": c.user_messages,
                    "tokens_total": c.tokens_total,
                    "estimated_cost": round(c.estimated_cost or 0, 6),
                    "tools_used": c.tools_used or [],
                    "transfer_requested": c.transfer_requested,
                    "transfer_reason": c.transfer_reason,
                    "channel": c.channel,
                    "contact_name": c.contact_name,
                    "contact_phone": c.contact_phone,
                    "sentiment_score": c.sentiment_score,
                    "lead_score": c.lead_score
                }
                for c in conversations
            ]
        }

    @staticmethod
    async def get_funnel_metrics(
        db: AsyncSession,
        client_slug: str,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Retorna metricas de funil de conversao"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        conditions = [
            ConversationMetrics.client_slug == client_slug,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        ]

        # Total de conversas iniciadas
        total_started = (await db.execute(
            select(func.count(ConversationMetrics.id)).where(*conditions)
        )).scalar() or 0

        # Conversas com produtos mostrados
        with_products = (await db.execute(
            select(func.count(ConversationMetrics.id)).where(
                *conditions,
                func.array_length(ConversationMetrics.products_shown, 1) > 0
            )
        )).scalar() or 0

        # Conversas com interesse em produtos
        with_interest = (await db.execute(
            select(func.count(ConversationMetrics.id)).where(
                *conditions,
                func.array_length(ConversationMetrics.products_interested, 1) > 0
            )
        )).scalar() or 0

        # Conversas transferidas (potencial fechamento)
        transferred = (await db.execute(
            select(func.count(ConversationMetrics.id)).where(
                *conditions,
                ConversationMetrics.transfer_requested == True
            )
        )).scalar() or 0

        # Conversas convertidas
        converted = (await db.execute(
            select(func.count(ConversationMetrics.id)).where(
                *conditions,
                ConversationMetrics.outcome == 'converted'
            )
        )).scalar() or 0

        # Tools mais usadas
        tools_query = select(
            func.unnest(ConversationMetrics.tools_used).label('tool'),
            func.count().label('count')
        ).where(*conditions).group_by('tool').order_by(func.count().desc()).limit(10)

        tools_result = await db.execute(tools_query)
        top_tools = [{"tool": row.tool, "count": row.count} for row in tools_result.all()]

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "funnel": [
                {
                    "stage": "started",
                    "label": "Conversas Iniciadas",
                    "count": total_started,
                    "percentage": 100
                },
                {
                    "stage": "products_shown",
                    "label": "Viram Produtos",
                    "count": with_products,
                    "percentage": round(with_products / total_started * 100, 1) if total_started else 0
                },
                {
                    "stage": "interested",
                    "label": "Demonstraram Interesse",
                    "count": with_interest,
                    "percentage": round(with_interest / total_started * 100, 1) if total_started else 0
                },
                {
                    "stage": "transferred",
                    "label": "Transferidas p/ Humano",
                    "count": transferred,
                    "percentage": round(transferred / total_started * 100, 1) if total_started else 0
                },
                {
                    "stage": "converted",
                    "label": "Convertidas",
                    "count": converted,
                    "percentage": round(converted / total_started * 100, 1) if total_started else 0
                }
            ],
            "top_tools": top_tools
        }

    @staticmethod
    async def get_product_analytics(
        db: AsyncSession,
        client_slug: str,
        start_date: date = None,
        end_date: date = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Retorna analytics de produtos mais populares"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Contar quantas vezes cada produto foi mostrado
        conditions = [
            ConversationMetrics.client_slug == client_slug,
            cast(ConversationMetrics.started_at, Date) >= start_date,
            cast(ConversationMetrics.started_at, Date) <= end_date
        ]

        # Query para produtos mostrados
        shown_query = select(
            func.unnest(ConversationMetrics.products_shown).label('product_id'),
            func.count().label('views')
        ).where(*conditions).group_by('product_id')

        shown_result = await db.execute(shown_query)
        shown_counts = {row.product_id: row.views for row in shown_result.all()}

        # Query para produtos com interesse
        interest_query = select(
            func.unnest(ConversationMetrics.products_interested).label('product_id'),
            func.count().label('interests')
        ).where(*conditions).group_by('product_id')

        interest_result = await db.execute(interest_query)
        interest_counts = {row.product_id: row.interests for row in interest_result.all()}

        # Combinar e buscar detalhes dos produtos
        all_product_ids = set(shown_counts.keys()) | set(interest_counts.keys())

        if not all_product_ids:
            return []

        # Buscar detalhes dos produtos
        products_query = select(Product).where(
            Product.id.in_(all_product_ids)
        )
        products_result = await db.execute(products_query)
        products = {p.id: p for p in products_result.scalars().all()}

        # Montar resultado
        analytics = []
        for pid in all_product_ids:
            product = products.get(pid)
            views = shown_counts.get(pid, 0)
            interests = interest_counts.get(pid, 0)

            analytics.append({
                "product_id": pid,
                "name": product.name if product else f"Produto #{pid}",
                "views": views,
                "interests": interests,
                "interest_rate": round(interests / views * 100, 1) if views else 0
            })

        # Ordenar por views
        analytics.sort(key=lambda x: x['views'], reverse=True)

        return analytics[:limit]

    @staticmethod
    async def export_data(
        db: AsyncSession,
        client_slug: str,
        start_date: date = None,
        end_date: date = None,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Exporta dados de analytics"""
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Buscar todas as conversas do periodo
        result = await db.execute(
            select(ConversationMetrics).where(
                ConversationMetrics.client_slug == client_slug,
                cast(ConversationMetrics.started_at, Date) >= start_date,
                cast(ConversationMetrics.started_at, Date) <= end_date
            ).order_by(ConversationMetrics.started_at)
        )
        conversations = result.scalars().all()

        data = {
            "export_date": datetime.utcnow().isoformat(),
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "client_slug": client_slug,
            "total_records": len(conversations),
            "records": [
                {
                    "conversation_id": c.conversation_id,
                    "started_at": c.started_at.isoformat() if c.started_at else None,
                    "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                    "first_response_at": c.first_response_at.isoformat() if c.first_response_at else None,
                    "total_messages": c.total_messages,
                    "ai_messages": c.ai_messages,
                    "user_messages": c.user_messages,
                    "tokens_input": c.tokens_input,
                    "tokens_output": c.tokens_output,
                    "tokens_total": c.tokens_total,
                    "estimated_cost_usd": c.estimated_cost,
                    "outcome": c.outcome,
                    "transfer_requested": c.transfer_requested,
                    "transfer_reason": c.transfer_reason,
                    "products_shown": c.products_shown or [],
                    "products_interested": c.products_interested or [],
                    "sentiment_score": c.sentiment_score,
                    "lead_score": c.lead_score,
                    "tools_used": c.tools_used or [],
                    "tools_count": c.tools_count,
                    "channel": c.channel,
                    "contact_phone": c.contact_phone,
                    "contact_name": c.contact_name
                }
                for c in conversations
            ]
        }

        return data
