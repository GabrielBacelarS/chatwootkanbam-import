"""
Lead Scoring Service - Calcula score de leads baseado em comportamento
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class ScoreAction(str, Enum):
    """Acoes que afetam o lead score"""
    # Interesse em produtos
    VIEWED_PRODUCT = "viewed_product"
    ASKED_PRICE = "asked_price"
    ASKED_AVAILABILITY = "asked_availability"
    COMPARED_PRODUCTS = "compared_products"

    # Intencao de compra
    ASKED_FINANCING = "asked_financing"
    ASKED_PAYMENT_OPTIONS = "asked_payment_options"
    ASKED_DELIVERY = "asked_delivery"
    ASKED_WARRANTY = "asked_warranty"

    # Acao concreta
    SCHEDULED_VISIT = "scheduled_visit"
    PROVIDED_CONTACT = "provided_contact"
    REQUESTED_TRANSFER = "requested_transfer"
    CONFIRMED_INTEREST = "confirmed_interest"

    # Engajamento
    MULTIPLE_MESSAGES = "multiple_messages"
    QUICK_RESPONSE = "quick_response"
    LONG_CONVERSATION = "long_conversation"

    # Negativos
    ABANDONED_EARLY = "abandoned_early"
    NO_RESPONSE = "no_response"
    NEGATIVE_SENTIMENT = "negative_sentiment"


@dataclass
class ScoringRule:
    """Regra de pontuacao"""
    action: ScoreAction
    points: int
    max_occurrences: int = 1  # Quantas vezes pode pontuar
    description: str = ""


# Regras de pontuacao padrao
DEFAULT_SCORING_RULES: List[ScoringRule] = [
    # Interesse em produtos (+10 a +15)
    ScoringRule(ScoreAction.VIEWED_PRODUCT, 10, max_occurrences=3, description="Visualizou produto"),
    ScoringRule(ScoreAction.ASKED_PRICE, 15, max_occurrences=2, description="Perguntou preco"),
    ScoringRule(ScoreAction.ASKED_AVAILABILITY, 12, max_occurrences=2, description="Perguntou disponibilidade"),
    ScoringRule(ScoreAction.COMPARED_PRODUCTS, 15, max_occurrences=1, description="Comparou produtos"),

    # Intencao de compra (+15 a +20)
    ScoringRule(ScoreAction.ASKED_FINANCING, 20, max_occurrences=1, description="Perguntou financiamento"),
    ScoringRule(ScoreAction.ASKED_PAYMENT_OPTIONS, 18, max_occurrences=1, description="Perguntou formas de pagamento"),
    ScoringRule(ScoreAction.ASKED_DELIVERY, 15, max_occurrences=1, description="Perguntou entrega"),
    ScoringRule(ScoreAction.ASKED_WARRANTY, 12, max_occurrences=1, description="Perguntou garantia"),

    # Acao concreta (+25 a +30)
    ScoringRule(ScoreAction.SCHEDULED_VISIT, 30, max_occurrences=1, description="Agendou visita"),
    ScoringRule(ScoreAction.PROVIDED_CONTACT, 25, max_occurrences=1, description="Forneceu contato"),
    ScoringRule(ScoreAction.REQUESTED_TRANSFER, 28, max_occurrences=1, description="Solicitou atendente"),
    ScoringRule(ScoreAction.CONFIRMED_INTEREST, 25, max_occurrences=1, description="Confirmou interesse"),

    # Engajamento (+5 a +10)
    ScoringRule(ScoreAction.MULTIPLE_MESSAGES, 5, max_occurrences=3, description="Enviou multiplas mensagens"),
    ScoringRule(ScoreAction.QUICK_RESPONSE, 8, max_occurrences=2, description="Respondeu rapidamente"),
    ScoringRule(ScoreAction.LONG_CONVERSATION, 10, max_occurrences=1, description="Conversa longa"),

    # Negativos (-10 a -20)
    ScoringRule(ScoreAction.ABANDONED_EARLY, -20, max_occurrences=1, description="Abandonou cedo"),
    ScoringRule(ScoreAction.NO_RESPONSE, -15, max_occurrences=1, description="Nao respondeu"),
    ScoringRule(ScoreAction.NEGATIVE_SENTIMENT, -10, max_occurrences=2, description="Sentimento negativo"),
]


class LeadScoringService:
    """Servico de calculo de lead score"""

    def __init__(self, rules: List[ScoringRule] = None):
        self.rules = rules or DEFAULT_SCORING_RULES
        self._rules_by_action = {r.action: r for r in self.rules}

    def calculate_score(
        self,
        actions: List[ScoreAction],
        base_score: int = 0
    ) -> int:
        """
        Calcula score baseado em lista de acoes.

        Args:
            actions: Lista de acoes realizadas pelo lead
            base_score: Score inicial (default 0)

        Returns:
            Score calculado (0-100)
        """
        score = base_score
        action_counts: Dict[ScoreAction, int] = {}

        for action in actions:
            # Contar ocorrencias
            action_counts[action] = action_counts.get(action, 0) + 1

            # Buscar regra
            rule = self._rules_by_action.get(action)
            if not rule:
                continue

            # Verificar limite de ocorrencias
            if action_counts[action] <= rule.max_occurrences:
                score += rule.points
                logger.debug(f"Lead Score: +{rule.points} por {rule.description}")

        # Normalizar para 0-100
        score = max(0, min(100, score))

        return score

    def calculate_from_conversation(
        self,
        messages: List[Dict[str, Any]],
        tools_used: List[str] = None,
        transfer_requested: bool = False,
        products_shown: int = 0,
        conversation_duration_minutes: float = 0
    ) -> Dict[str, Any]:
        """
        Calcula score analisando dados da conversa.

        Args:
            messages: Historico de mensagens da conversa
            tools_used: Lista de tools usadas pelo agente
            transfer_requested: Se foi solicitada transferencia
            products_shown: Quantidade de produtos mostrados
            conversation_duration_minutes: Duracao da conversa em minutos

        Returns:
            Dict com score e breakdown
        """
        actions: List[ScoreAction] = []
        breakdown: List[Dict[str, Any]] = []

        tools_used = tools_used or []
        user_messages = [m for m in messages if m.get("role") == "user"]
        user_text = " ".join(m.get("content", "") for m in user_messages).lower()

        # Analisar tools usadas
        if "buscar_produtos" in tools_used:
            actions.append(ScoreAction.VIEWED_PRODUCT)
            breakdown.append({"action": "viewed_product", "trigger": "buscar_produtos tool"})

        if "calcular_financiamento" in tools_used:
            actions.append(ScoreAction.ASKED_FINANCING)
            breakdown.append({"action": "asked_financing", "trigger": "calcular_financiamento tool"})

        if "agendar_visita" in tools_used:
            actions.append(ScoreAction.SCHEDULED_VISIT)
            breakdown.append({"action": "scheduled_visit", "trigger": "agendar_visita tool"})

        if "transferir_atendimento" in tools_used or transfer_requested:
            actions.append(ScoreAction.REQUESTED_TRANSFER)
            breakdown.append({"action": "requested_transfer", "trigger": "transferencia solicitada"})

        # Analisar texto do usuario
        price_keywords = ["preco", "preço", "quanto", "valor", "custa", "custar"]
        if any(kw in user_text for kw in price_keywords):
            actions.append(ScoreAction.ASKED_PRICE)
            breakdown.append({"action": "asked_price", "trigger": "perguntou preco"})

        availability_keywords = ["disponivel", "disponível", "tem", "estoque", "pronta entrega"]
        if any(kw in user_text for kw in availability_keywords):
            actions.append(ScoreAction.ASKED_AVAILABILITY)
            breakdown.append({"action": "asked_availability", "trigger": "perguntou disponibilidade"})

        payment_keywords = ["parcela", "entrada", "pagar", "pagamento", "cartao", "pix", "boleto"]
        if any(kw in user_text for kw in payment_keywords):
            actions.append(ScoreAction.ASKED_PAYMENT_OPTIONS)
            breakdown.append({"action": "asked_payment_options", "trigger": "perguntou pagamento"})

        delivery_keywords = ["entrega", "entregar", "frete", "envio", "enviar"]
        if any(kw in user_text for kw in delivery_keywords):
            actions.append(ScoreAction.ASKED_DELIVERY)
            breakdown.append({"action": "asked_delivery", "trigger": "perguntou entrega"})

        warranty_keywords = ["garantia", "trocar", "defeito", "garantir"]
        if any(kw in user_text for kw in warranty_keywords):
            actions.append(ScoreAction.ASKED_WARRANTY)
            breakdown.append({"action": "asked_warranty", "trigger": "perguntou garantia"})

        interest_keywords = ["quero", "vou querer", "fechado", "combinado", "interesse", "gostei"]
        if any(kw in user_text for kw in interest_keywords):
            actions.append(ScoreAction.CONFIRMED_INTEREST)
            breakdown.append({"action": "confirmed_interest", "trigger": "confirmou interesse"})

        # Analisar engajamento
        if len(user_messages) >= 5:
            actions.append(ScoreAction.MULTIPLE_MESSAGES)
            breakdown.append({"action": "multiple_messages", "trigger": f"{len(user_messages)} mensagens"})

        if len(user_messages) >= 8:
            actions.append(ScoreAction.MULTIPLE_MESSAGES)  # Bonus por muitas mensagens

        if conversation_duration_minutes >= 5:
            actions.append(ScoreAction.LONG_CONVERSATION)
            breakdown.append({"action": "long_conversation", "trigger": f"{conversation_duration_minutes:.1f} minutos"})

        # Analisar produtos
        if products_shown >= 2:
            actions.append(ScoreAction.COMPARED_PRODUCTS)
            breakdown.append({"action": "compared_products", "trigger": f"{products_shown} produtos mostrados"})

        # Calcular score final
        score = self.calculate_score(actions)

        # Classificacao
        if score >= 80:
            classification = "hot"
            classification_label = "Lead Quente"
        elif score >= 50:
            classification = "warm"
            classification_label = "Lead Morno"
        elif score >= 25:
            classification = "cold"
            classification_label = "Lead Frio"
        else:
            classification = "unqualified"
            classification_label = "Nao Qualificado"

        return {
            "score": score,
            "classification": classification,
            "classification_label": classification_label,
            "actions_detected": len(actions),
            "breakdown": breakdown
        }

    @staticmethod
    def get_score_classification(score: int) -> str:
        """Retorna classificacao baseada no score"""
        if score >= 80:
            return "hot"
        elif score >= 50:
            return "warm"
        elif score >= 25:
            return "cold"
        else:
            return "unqualified"


# Instancia global para uso facil
lead_scoring = LeadScoringService()
