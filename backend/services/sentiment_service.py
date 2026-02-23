"""
Sentiment Analysis Service - Analise de sentimento usando IA
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging
import re

logger = logging.getLogger(__name__)


class SentimentLevel(str, Enum):
    """Niveis de sentimento"""
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


@dataclass
class SentimentResult:
    """Resultado da analise de sentimento"""
    score: float  # -1.0 a 1.0
    level: SentimentLevel
    confidence: float  # 0.0 a 1.0
    keywords_positive: List[str]
    keywords_negative: List[str]
    should_transfer: bool = False
    transfer_reason: Optional[str] = None


class SentimentService:
    """Servico de analise de sentimento"""

    # Palavras-chave para analise rapida (fallback)
    POSITIVE_KEYWORDS = [
        "obrigado", "obrigada", "agradeço", "gostei", "perfeito", "otimo", "ótimo",
        "excelente", "maravilhoso", "incrivel", "incrível", "show", "top", "massa",
        "adorei", "amei", "legal", "bom", "boa", "bacana", "interessante", "quero",
        "vou querer", "fechado", "combinado", "beleza", "sim", "pode", "ok", "blz",
        "satisfeito", "feliz", "animado", "ansioso"
    ]

    NEGATIVE_KEYWORDS = [
        "ruim", "pessimo", "péssimo", "horrivel", "horrível", "nao gostei", "não gostei",
        "decepcionado", "frustrado", "irritado", "raiva", "absurdo", "vergonha",
        "enganado", "mentira", "golpe", "reclamar", "reclamacao", "reclamação",
        "problema", "errado", "erro", "demora", "lento", "caro", "caríssimo",
        "nao quero", "não quero", "desisto", "cancelar", "devolver", "reembolso",
        "insatisfeito", "triste", "bravo", "chateado"
    ]

    FRUSTRATION_KEYWORDS = [
        "ja falei", "já falei", "nao entende", "não entende", "quantas vezes",
        "toda hora", "sempre", "nunca", "impossivel", "impossível", "ninguem",
        "ninguém", "ridiculo", "ridículo", "absurdo", "inaceitavel", "inaceitável",
        "vou processar", "procon", "reclame aqui", "advogado", "justica", "justiça"
    ]

    @staticmethod
    async def analyze_with_ai(
        api_key: str,
        text: str,
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> SentimentResult:
        """
        Analisa sentimento usando IA.

        Args:
            api_key: Chave de API
            text: Texto para analisar
            provider: Provedor de IA (openai)
            model: Modelo a usar

        Returns:
            SentimentResult com analise completa
        """
        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=api_key)

            prompt = f"""Analise o sentimento do texto abaixo e retorne APENAS um JSON no formato:
{{
    "score": <numero de -1.0 a 1.0>,
    "level": <"very_positive", "positive", "neutral", "negative" ou "very_negative">,
    "confidence": <numero de 0.0 a 1.0>,
    "keywords_positive": [lista de palavras positivas encontradas],
    "keywords_negative": [lista de palavras negativas encontradas],
    "should_transfer": <true se cliente parece muito frustrado>,
    "transfer_reason": <motivo se should_transfer=true, null caso contrario>
}}

Texto para analisar:
"{text}"

IMPORTANTE:
- score: -1.0 = muito negativo, 0 = neutro, 1.0 = muito positivo
- should_transfer: true apenas se cliente demonstrar frustração intensa
- Retorne APENAS o JSON, sem explicações"""

            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=300
            )

            result_text = response.choices[0].message.content.strip()

            # Extrair JSON
            import json
            # Tentar extrair JSON do texto
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_text = json_match.group()

            data = json.loads(result_text)

            return SentimentResult(
                score=float(data.get("score", 0)),
                level=SentimentLevel(data.get("level", "neutral")),
                confidence=float(data.get("confidence", 0.8)),
                keywords_positive=data.get("keywords_positive", []),
                keywords_negative=data.get("keywords_negative", []),
                should_transfer=data.get("should_transfer", False),
                transfer_reason=data.get("transfer_reason")
            )

        except Exception as e:
            logger.warning(f"Erro na analise de sentimento com IA: {e}. Usando fallback.")
            return SentimentService.analyze_keywords(text)

    @staticmethod
    def analyze_keywords(text: str) -> SentimentResult:
        """
        Analisa sentimento usando keywords (fallback rapido).

        Args:
            text: Texto para analisar

        Returns:
            SentimentResult com analise baseada em keywords
        """
        text_lower = text.lower()

        # Encontrar keywords
        positive_found = [kw for kw in SentimentService.POSITIVE_KEYWORDS if kw in text_lower]
        negative_found = [kw for kw in SentimentService.NEGATIVE_KEYWORDS if kw in text_lower]
        frustration_found = [kw for kw in SentimentService.FRUSTRATION_KEYWORDS if kw in text_lower]

        # Calcular score
        positive_count = len(positive_found)
        negative_count = len(negative_found) + len(frustration_found) * 2  # Frustracao pesa mais

        total = positive_count + negative_count
        if total == 0:
            score = 0.0
        else:
            score = (positive_count - negative_count) / max(total, 1)
            score = max(-1.0, min(1.0, score))  # Normalizar

        # Determinar nivel
        if score >= 0.6:
            level = SentimentLevel.VERY_POSITIVE
        elif score >= 0.2:
            level = SentimentLevel.POSITIVE
        elif score >= -0.2:
            level = SentimentLevel.NEUTRAL
        elif score >= -0.6:
            level = SentimentLevel.NEGATIVE
        else:
            level = SentimentLevel.VERY_NEGATIVE

        # Verificar se deve transferir
        should_transfer = len(frustration_found) >= 2 or level == SentimentLevel.VERY_NEGATIVE
        transfer_reason = None
        if should_transfer:
            if frustration_found:
                transfer_reason = f"Cliente demonstra frustracao: {', '.join(frustration_found[:3])}"
            else:
                transfer_reason = "Sentimento muito negativo detectado"

        return SentimentResult(
            score=round(score, 2),
            level=level,
            confidence=0.7 if total > 0 else 0.5,  # Menor confianca sem IA
            keywords_positive=positive_found[:5],
            keywords_negative=negative_found[:5] + frustration_found[:3],
            should_transfer=should_transfer,
            transfer_reason=transfer_reason
        )

    @staticmethod
    def analyze_conversation_trend(
        messages: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analisa tendencia de sentimento ao longo da conversa.

        Args:
            messages: Lista de mensagens da conversa

        Returns:
            Dict com analise de tendencia
        """
        user_messages = [m for m in messages if m.get("role") == "user"]

        if not user_messages:
            return {
                "trend": "neutral",
                "average_score": 0,
                "first_half_score": 0,
                "second_half_score": 0,
                "improving": False
            }

        # Analisar cada mensagem
        scores = []
        for msg in user_messages:
            content = msg.get("content", "")
            if content:
                result = SentimentService.analyze_keywords(content)
                scores.append(result.score)

        if not scores:
            return {
                "trend": "neutral",
                "average_score": 0,
                "first_half_score": 0,
                "second_half_score": 0,
                "improving": False
            }

        # Calcular medias
        average = sum(scores) / len(scores)

        mid = len(scores) // 2
        first_half = sum(scores[:mid]) / mid if mid > 0 else average
        second_half = sum(scores[mid:]) / (len(scores) - mid) if len(scores) > mid else average

        # Determinar tendencia
        if second_half > first_half + 0.2:
            trend = "improving"
        elif second_half < first_half - 0.2:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "average_score": round(average, 2),
            "first_half_score": round(first_half, 2),
            "second_half_score": round(second_half, 2),
            "improving": second_half > first_half,
            "message_count": len(scores)
        }

    @staticmethod
    def get_level_emoji(level: SentimentLevel) -> str:
        """Retorna emoji para o nivel de sentimento"""
        emojis = {
            SentimentLevel.VERY_POSITIVE: "😄",
            SentimentLevel.POSITIVE: "🙂",
            SentimentLevel.NEUTRAL: "😐",
            SentimentLevel.NEGATIVE: "😕",
            SentimentLevel.VERY_NEGATIVE: "😠"
        }
        return emojis.get(level, "😐")

    @staticmethod
    def get_level_label(level: SentimentLevel) -> str:
        """Retorna label em portugues para o nivel"""
        labels = {
            SentimentLevel.VERY_POSITIVE: "Muito Positivo",
            SentimentLevel.POSITIVE: "Positivo",
            SentimentLevel.NEUTRAL: "Neutro",
            SentimentLevel.NEGATIVE: "Negativo",
            SentimentLevel.VERY_NEGATIVE: "Muito Negativo"
        }
        return labels.get(level, "Neutro")
