"""
Rotas de Analytics - Dashboard e Metricas
"""
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/{slug}/overview")
async def get_analytics_overview(
    slug: str,
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna visao geral de analytics do cliente.

    Inclui:
    - Total de conversas
    - Distribuicao por outcome (convertido, transferido, abandonado)
    - Total de tokens consumidos
    - Custos estimados
    - Taxas de conversao e transferencia
    """
    try:
        return await AnalyticsService.get_overview(
            db=db,
            client_slug=slug,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/daily")
async def get_daily_metrics(
    slug: str,
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna metricas agregadas por dia.

    Util para graficos de tendencia e comparativos.
    """
    try:
        return await AnalyticsService.get_daily_metrics(
            db=db,
            client_slug=slug,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/conversations")
async def get_conversations(
    slug: str,
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    outcome: Optional[str] = Query(None, description="Filtrar por outcome (converted, transferred, abandoned)"),
    limit: int = Query(50, ge=1, le=100, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginacao"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna lista detalhada de conversas com metricas.

    Suporta paginacao e filtro por outcome.
    """
    try:
        return await AnalyticsService.get_conversation_details(
            db=db,
            client_slug=slug,
            start_date=start_date,
            end_date=end_date,
            outcome=outcome,
            limit=limit,
            offset=offset
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/funnel")
async def get_funnel_metrics(
    slug: str,
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna metricas de funil de conversao.

    Mostra a progressao das conversas:
    1. Iniciadas
    2. Viram produtos
    3. Demonstraram interesse
    4. Transferidas para humano
    5. Convertidas
    """
    try:
        return await AnalyticsService.get_funnel_metrics(
            db=db,
            client_slug=slug,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/products")
async def get_product_analytics(
    slug: str,
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100, description="Limite de resultados"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna analytics dos produtos mais populares.

    Mostra quantas vezes cada produto foi:
    - Visualizado (mostrado ao cliente)
    - Gerou interesse
    - Taxa de interesse (interesse / visualizacoes)
    """
    try:
        return await AnalyticsService.get_product_analytics(
            db=db,
            client_slug=slug,
            start_date=start_date,
            end_date=end_date,
            limit=limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/costs")
async def get_costs_breakdown(
    slug: str,
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna breakdown de custos por periodo.

    Inclui:
    - Custo total
    - Custo por dia
    - Custo medio por conversa
    - Projecao mensal
    """
    try:
        # Obter metricas diarias
        daily = await AnalyticsService.get_daily_metrics(
            db=db,
            client_slug=slug,
            start_date=start_date,
            end_date=end_date
        )

        # Calcular totais
        total_cost = sum(d.get('cost_usd', 0) for d in daily)
        total_tokens = sum(d.get('tokens', 0) for d in daily)
        total_conversations = sum(d.get('conversations', 0) for d in daily)
        num_days = len(daily) if daily else 1

        # Projecao mensal (baseado na media diaria)
        daily_avg = total_cost / num_days if num_days else 0
        monthly_projection = daily_avg * 30

        return {
            "period": {
                "start": (start_date or date.today() - timedelta(days=30)).isoformat(),
                "end": (end_date or date.today()).isoformat(),
                "days": num_days
            },
            "costs": {
                "total_usd": round(total_cost, 4),
                "daily_average_usd": round(daily_avg, 4),
                "per_conversation_usd": round(total_cost / total_conversations, 6) if total_conversations else 0,
                "monthly_projection_usd": round(monthly_projection, 2)
            },
            "tokens": {
                "total": total_tokens,
                "daily_average": round(total_tokens / num_days) if num_days else 0,
                "per_conversation": round(total_tokens / total_conversations) if total_conversations else 0
            },
            "conversations": {
                "total": total_conversations,
                "daily_average": round(total_conversations / num_days, 1) if num_days else 0
            },
            "daily_breakdown": [
                {
                    "date": d.get('date'),
                    "cost_usd": d.get('cost_usd', 0),
                    "tokens": d.get('tokens', 0),
                    "conversations": d.get('conversations', 0)
                }
                for d in daily
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/export")
async def export_analytics(
    slug: str,
    start_date: Optional[date] = Query(None, description="Data inicial (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="Data final (YYYY-MM-DD)"),
    format: str = Query("json", description="Formato de exportacao (json)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Exporta dados de analytics.

    Retorna todos os dados de conversas do periodo selecionado
    em formato JSON para integracao com outras ferramentas.
    """
    try:
        return await AnalyticsService.export_data(
            db=db,
            client_slug=slug,
            start_date=start_date,
            end_date=end_date,
            format=format
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{slug}/summary")
async def get_quick_summary(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Retorna resumo rapido para dashboard.

    Inclui dados de hoje, ontem, ultimos 7 dias e ultimos 30 dias.
    """
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        # Metricas de hoje
        today_data = await AnalyticsService.get_overview(
            db=db, client_slug=slug, start_date=today, end_date=today
        )

        # Metricas de ontem
        yesterday_data = await AnalyticsService.get_overview(
            db=db, client_slug=slug, start_date=yesterday, end_date=yesterday
        )

        # Metricas da semana
        week_data = await AnalyticsService.get_overview(
            db=db, client_slug=slug, start_date=week_ago, end_date=today
        )

        # Metricas do mes
        month_data = await AnalyticsService.get_overview(
            db=db, client_slug=slug, start_date=month_ago, end_date=today
        )

        return {
            "today": {
                "conversations": today_data["conversations"]["total"],
                "cost_usd": today_data["costs"]["total_usd"],
                "conversion_rate": today_data["rates"]["conversion"]
            },
            "yesterday": {
                "conversations": yesterday_data["conversations"]["total"],
                "cost_usd": yesterday_data["costs"]["total_usd"],
                "conversion_rate": yesterday_data["rates"]["conversion"]
            },
            "week": {
                "conversations": week_data["conversations"]["total"],
                "cost_usd": week_data["costs"]["total_usd"],
                "conversion_rate": week_data["rates"]["conversion"]
            },
            "month": {
                "conversations": month_data["conversations"]["total"],
                "cost_usd": month_data["costs"]["total_usd"],
                "conversion_rate": month_data["rates"]["conversion"],
                "tokens": month_data["tokens"]["total"]
            },
            "trends": {
                "conversations_vs_yesterday": (
                    today_data["conversations"]["total"] - yesterday_data["conversations"]["total"]
                ),
                "cost_vs_yesterday": round(
                    today_data["costs"]["total_usd"] - yesterday_data["costs"]["total_usd"], 4
                )
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
