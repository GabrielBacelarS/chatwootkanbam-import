"""
A/B Testing Service - Gerenciamento de testes A/B de prompts
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import random
import math
import logging

from backend.models.ab_test import ABTest, ABTestResult, ABTestStatus

logger = logging.getLogger(__name__)


class ABTestingService:
    """Servico de A/B Testing"""

    @staticmethod
    async def create_test(
        db: AsyncSession,
        client_slug: str,
        name: str,
        variants: List[Dict[str, Any]],
        description: str = None,
        success_metric: str = "conversion_rate",
        min_sample_size: int = 100,
        confidence_level: float = 0.95
    ) -> ABTest:
        """
        Cria um novo teste A/B.

        Args:
            client_slug: Slug do cliente
            name: Nome do teste
            variants: Lista de variantes com id, name, prompt, traffic_percentage
            description: Descricao do teste
            success_metric: Metrica de sucesso
            min_sample_size: Tamanho minimo da amostra por variante
            confidence_level: Nivel de confianca estatistica

        Returns:
            ABTest criado
        """
        # Validar que porcentagens somam 100
        total_traffic = sum(v.get("traffic_percentage", 0) for v in variants)
        if total_traffic != 100:
            raise ValueError(f"Porcentagens devem somar 100, somam {total_traffic}")

        # Garantir IDs unicos
        for i, v in enumerate(variants):
            if "id" not in v:
                v["id"] = chr(65 + i)  # A, B, C, ...

        test = ABTest(
            client_slug=client_slug,
            name=name,
            description=description,
            variants=variants,
            success_metric=success_metric,
            min_sample_size=min_sample_size,
            confidence_level=confidence_level,
            status=ABTestStatus.DRAFT
        )

        db.add(test)
        await db.commit()
        await db.refresh(test)

        logger.info(f"[{client_slug}] Teste A/B criado: {name} com {len(variants)} variantes")
        return test

    @staticmethod
    async def start_test(db: AsyncSession, test_id: int) -> ABTest:
        """Inicia um teste A/B"""
        result = await db.execute(select(ABTest).where(ABTest.id == test_id))
        test = result.scalar_one_or_none()

        if not test:
            raise ValueError("Teste nao encontrado")

        if test.status == ABTestStatus.RUNNING:
            raise ValueError("Teste ja esta em execucao")

        test.status = ABTestStatus.RUNNING
        test.started_at = datetime.utcnow()

        await db.commit()
        logger.info(f"[{test.client_slug}] Teste A/B iniciado: {test.name}")
        return test

    @staticmethod
    async def pause_test(db: AsyncSession, test_id: int) -> ABTest:
        """Pausa um teste A/B"""
        result = await db.execute(select(ABTest).where(ABTest.id == test_id))
        test = result.scalar_one_or_none()

        if not test:
            raise ValueError("Teste nao encontrado")

        test.status = ABTestStatus.PAUSED
        await db.commit()
        return test

    @staticmethod
    async def stop_test(db: AsyncSession, test_id: int) -> ABTest:
        """Encerra um teste A/B e calcula vencedor"""
        result = await db.execute(select(ABTest).where(ABTest.id == test_id))
        test = result.scalar_one_or_none()

        if not test:
            raise ValueError("Teste nao encontrado")

        test.status = ABTestStatus.COMPLETED
        test.ended_at = datetime.utcnow()

        # Calcular resultados
        stats = await ABTestingService.calculate_statistics(db, test_id)

        # Determinar vencedor
        if stats.get("is_significant"):
            test.is_significant = True
            test.winner_variant_id = stats.get("winner")

        await db.commit()
        logger.info(f"[{test.client_slug}] Teste A/B encerrado: {test.name}, vencedor: {test.winner_variant_id}")
        return test

    @staticmethod
    async def get_variant_for_conversation(
        db: AsyncSession,
        client_slug: str,
        conversation_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Seleciona variante para uma conversa baseado no teste A/B ativo.

        Args:
            client_slug: Slug do cliente
            conversation_id: ID da conversa (usado como seed para consistencia)

        Returns:
            Variante selecionada ou None se nao houver teste ativo
        """
        # Buscar teste ativo
        result = await db.execute(
            select(ABTest).where(
                ABTest.client_slug == client_slug,
                ABTest.status == ABTestStatus.RUNNING
            )
        )
        test = result.scalar_one_or_none()

        if not test or not test.variants:
            return None

        # Usar conversation_id como seed para garantir consistencia
        # (mesma conversa sempre recebe mesma variante)
        random.seed(conversation_id)

        # Selecionar variante baseado em porcentagem
        rand = random.random() * 100
        cumulative = 0

        for variant in test.variants:
            cumulative += variant.get("traffic_percentage", 0)
            if rand <= cumulative:
                return {
                    "test_id": test.id,
                    "test_name": test.name,
                    "variant_id": variant["id"],
                    "variant_name": variant.get("name", variant["id"]),
                    "prompt": variant.get("prompt", "")
                }

        # Fallback para ultima variante
        last_variant = test.variants[-1]
        return {
            "test_id": test.id,
            "test_name": test.name,
            "variant_id": last_variant["id"],
            "variant_name": last_variant.get("name", last_variant["id"]),
            "prompt": last_variant.get("prompt", "")
        }

    @staticmethod
    async def record_result(
        db: AsyncSession,
        test_id: int,
        variant_id: str,
        conversation_id: int,
        converted: bool = False,
        transferred: bool = False,
        message_count: int = 0,
        sentiment_score: float = None,
        lead_score: int = None
    ) -> ABTestResult:
        """Registra resultado de uma conversa no teste"""
        result = ABTestResult(
            test_id=test_id,
            variant_id=variant_id,
            conversation_id=conversation_id,
            converted=converted,
            transferred=transferred,
            message_count=message_count,
            sentiment_score=sentiment_score,
            lead_score=lead_score
        )

        db.add(result)
        await db.commit()
        return result

    @staticmethod
    async def calculate_statistics(
        db: AsyncSession,
        test_id: int
    ) -> Dict[str, Any]:
        """
        Calcula estatisticas do teste A/B.

        Usa teste Z para duas proporcoes.

        Returns:
            Dict com estatisticas por variante e resultado geral
        """
        # Buscar teste
        result = await db.execute(select(ABTest).where(ABTest.id == test_id))
        test = result.scalar_one_or_none()

        if not test:
            raise ValueError("Teste nao encontrado")

        # Buscar resultados por variante
        variant_stats = {}
        for variant in test.variants:
            vid = variant["id"]

            # Contar total
            count_query = select(func.count(ABTestResult.id)).where(
                ABTestResult.test_id == test_id,
                ABTestResult.variant_id == vid
            )
            total = (await db.execute(count_query)).scalar() or 0

            # Contar conversoes
            conversion_query = select(func.count(ABTestResult.id)).where(
                ABTestResult.test_id == test_id,
                ABTestResult.variant_id == vid,
                ABTestResult.converted == True
            )
            conversions = (await db.execute(conversion_query)).scalar() or 0

            # Contar transferencias
            transfer_query = select(func.count(ABTestResult.id)).where(
                ABTestResult.test_id == test_id,
                ABTestResult.variant_id == vid,
                ABTestResult.transferred == True
            )
            transfers = (await db.execute(transfer_query)).scalar() or 0

            # Media de mensagens
            msg_query = select(func.avg(ABTestResult.message_count)).where(
                ABTestResult.test_id == test_id,
                ABTestResult.variant_id == vid
            )
            avg_messages = (await db.execute(msg_query)).scalar() or 0

            # Media de sentimento
            sentiment_query = select(func.avg(ABTestResult.sentiment_score)).where(
                ABTestResult.test_id == test_id,
                ABTestResult.variant_id == vid,
                ABTestResult.sentiment_score.isnot(None)
            )
            avg_sentiment = (await db.execute(sentiment_query)).scalar() or 0

            conversion_rate = (conversions / total * 100) if total > 0 else 0
            transfer_rate = (transfers / total * 100) if total > 0 else 0

            variant_stats[vid] = {
                "variant_id": vid,
                "variant_name": variant.get("name", vid),
                "sample_size": total,
                "conversions": conversions,
                "conversion_rate": round(conversion_rate, 2),
                "transfers": transfers,
                "transfer_rate": round(transfer_rate, 2),
                "avg_messages": round(float(avg_messages), 1),
                "avg_sentiment": round(float(avg_sentiment), 2) if avg_sentiment else None
            }

        # Calcular significancia estatistica (teste Z para duas proporcoes)
        variants_list = list(variant_stats.values())

        is_significant = False
        winner = None
        p_value = None
        z_score = None

        if len(variants_list) >= 2:
            v1, v2 = variants_list[0], variants_list[1]

            n1, n2 = v1["sample_size"], v2["sample_size"]

            if n1 >= test.min_sample_size and n2 >= test.min_sample_size:
                # Determinar metrica a comparar
                if test.success_metric == "conversion_rate":
                    p1 = v1["conversion_rate"] / 100
                    p2 = v2["conversion_rate"] / 100
                elif test.success_metric == "transfer_rate":
                    # Menor taxa de transferencia e melhor
                    p1 = 1 - (v1["transfer_rate"] / 100)
                    p2 = 1 - (v2["transfer_rate"] / 100)
                else:
                    p1 = v1["conversion_rate"] / 100
                    p2 = v2["conversion_rate"] / 100

                # Calcular Z-score
                p_pooled = (p1 * n1 + p2 * n2) / (n1 + n2)

                if p_pooled > 0 and p_pooled < 1:
                    se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))
                    if se > 0:
                        z_score = (p1 - p2) / se

                        # Calcular p-value aproximado (distribuicao normal)
                        # Usando aproximacao simples
                        p_value = 2 * (1 - ABTestingService._normal_cdf(abs(z_score)))

                        # Verificar significancia
                        alpha = 1 - test.confidence_level
                        is_significant = p_value < alpha

                        if is_significant:
                            winner = v1["variant_id"] if p1 > p2 else v2["variant_id"]

        return {
            "test_id": test_id,
            "test_name": test.name,
            "status": test.status,
            "success_metric": test.success_metric,
            "variants": variant_stats,
            "is_significant": is_significant,
            "winner": winner,
            "p_value": round(p_value, 4) if p_value else None,
            "z_score": round(z_score, 2) if z_score else None,
            "confidence_level": test.confidence_level,
            "min_sample_reached": all(
                v["sample_size"] >= test.min_sample_size for v in variants_list
            )
        }

    @staticmethod
    def _normal_cdf(x: float) -> float:
        """Funcao de distribuicao cumulativa normal padrao (aproximacao)"""
        # Aproximacao de Abramowitz e Stegun
        t = 1.0 / (1.0 + 0.2316419 * abs(x))
        d = 0.3989423 * math.exp(-x * x / 2.0)
        p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))

        if x > 0:
            return 1.0 - p
        return p

    @staticmethod
    async def list_tests(
        db: AsyncSession,
        client_slug: str,
        status: str = None
    ) -> List[Dict[str, Any]]:
        """Lista testes A/B do cliente"""
        query = select(ABTest).where(ABTest.client_slug == client_slug)

        if status:
            query = query.where(ABTest.status == status)

        query = query.order_by(ABTest.created_at.desc())

        result = await db.execute(query)
        tests = result.scalars().all()

        return [t.to_dict() for t in tests]
