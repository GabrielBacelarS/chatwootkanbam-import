"""
Servico de pontuacao automatica para testes de agentes IA
Avalia respostas baseado em criterios configurados
"""
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TestScoringService:
    """Servico para avaliacao automatica de respostas de agentes IA"""

    @staticmethod
    def calculate_score(
        input_message: str,
        ai_response: str,
        tools_used: List[str],
        expected_tools: Optional[List[str]] = None,
        expected_keywords: Optional[List[str]] = None,
        should_not_contain: Optional[List[str]] = None,
        weight_tools: int = 10,
        weight_keywords: int = 10,
        weight_no_errors: int = 10,
        weight_quality: int = 5
    ) -> Tuple[float, Dict, List[str]]:
        """
        Calcula pontuacao de 0-10 para uma resposta do agente.

        Returns:
            Tuple[float, Dict, List[str]]: (score, breakdown, issues)
            - score: Nota final de 0 a 10
            - breakdown: Detalhamento por criterio
            - issues: Lista de problemas encontrados
        """
        breakdown = {}
        issues = []
        total_weight = 0
        weighted_score = 0

        # 1. Avaliacao de Tools Usadas
        if expected_tools is not None:
            tool_score, tool_details = TestScoringService._score_tools(
                expected=expected_tools,
                actual=tools_used
            )
            breakdown["tools"] = {
                "score": tool_score,
                "weight": weight_tools,
                "expected": expected_tools,
                "actual": tools_used,
                **tool_details
            }
            weighted_score += tool_score * weight_tools
            total_weight += weight_tools

            # Adicionar issues de tools
            if tool_details.get("missing"):
                issues.append(f"Tools nao usadas: {', '.join(tool_details['missing'])}")
            if tool_details.get("extra") and expected_tools:
                issues.append(f"Tools extras: {', '.join(tool_details['extra'])}")

        # 2. Avaliacao de Keywords
        if expected_keywords:
            keyword_score, found, missing = TestScoringService._score_keywords(
                keywords=expected_keywords,
                text=ai_response.lower()
            )
            breakdown["keywords"] = {
                "score": keyword_score,
                "weight": weight_keywords,
                "expected": expected_keywords,
                "found": found,
                "missing": missing
            }
            weighted_score += keyword_score * weight_keywords
            total_weight += weight_keywords

            if missing:
                issues.append(f"Palavras-chave ausentes: {', '.join(missing)}")

        # 3. Avaliacao de Conteudo Proibido
        if should_not_contain:
            forbidden_score, found_forbidden = TestScoringService._score_forbidden(
                forbidden=should_not_contain,
                text=ai_response.lower()
            )
            breakdown["no_errors"] = {
                "score": forbidden_score,
                "weight": weight_no_errors,
                "forbidden": should_not_contain,
                "found": found_forbidden
            }
            weighted_score += forbidden_score * weight_no_errors
            total_weight += weight_no_errors

            if found_forbidden:
                issues.append(f"Conteudo proibido: {', '.join(found_forbidden)}")

        # 4. Avaliacao de Qualidade
        quality_score, quality_issues = TestScoringService._score_quality(ai_response)
        breakdown["quality"] = {
            "score": quality_score,
            "weight": weight_quality,
            "checks": ["tamanho", "completude", "formatacao"]
        }
        weighted_score += quality_score * weight_quality
        total_weight += weight_quality

        if quality_issues:
            issues.extend(quality_issues)

        # Calcular nota final
        if total_weight > 0:
            final_score = weighted_score / total_weight
        else:
            final_score = 0

        # Limitar entre 0 e 10
        final_score = max(0, min(10, final_score))

        logger.info(f"Score calculado: {final_score:.2f} | Issues: {len(issues)}")

        return round(final_score, 2), breakdown, issues

    @staticmethod
    def _score_tools(expected: List[str], actual: List[str]) -> Tuple[float, Dict]:
        """
        Avalia se as tools corretas foram usadas.

        Criterios:
        - Se nao esperava nenhuma tool e nao usou: 10
        - Se esperava tools: pontua pela cobertura
        - Penaliza tools extras nao esperadas (levemente)
        """
        expected_set = set(expected or [])
        actual_set = set(actual or [])

        details = {
            "missing": list(expected_set - actual_set),
            "extra": list(actual_set - expected_set),
            "matched": list(expected_set & actual_set)
        }

        # Caso nao esperava nenhuma tool
        if not expected_set:
            # Se usou tools quando nao devia, penaliza levemente
            if actual_set:
                return 8.0, details
            return 10.0, details

        # Cobertura: quantas das esperadas foram usadas
        if expected_set:
            coverage = len(expected_set & actual_set) / len(expected_set)
        else:
            coverage = 1.0

        # Precisao: penalizar tools extras (levemente)
        if actual_set:
            precision = len(expected_set & actual_set) / len(actual_set)
        else:
            precision = 0.0 if expected_set else 1.0

        # Score combina cobertura (70%) e precisao (30%)
        score = (coverage * 0.7 + precision * 0.3) * 10

        return round(score, 2), details

    @staticmethod
    def _score_keywords(keywords: List[str], text: str) -> Tuple[float, List[str], List[str]]:
        """
        Avalia presenca de keywords na resposta.
        Busca parcial (substring) para cada keyword.
        """
        found = []
        missing = []

        text_lower = text.lower()

        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in text_lower:
                found.append(kw)
            else:
                missing.append(kw)

        if not keywords:
            return 10.0, found, missing

        score = (len(found) / len(keywords)) * 10

        return round(score, 2), found, missing

    @staticmethod
    def _score_forbidden(forbidden: List[str], text: str) -> Tuple[float, List[str]]:
        """
        Verifica se resposta contem conteudo proibido.
        Cada palavra proibida encontrada reduz a nota.
        """
        found = []
        text_lower = text.lower()

        for word in forbidden:
            if word.lower() in text_lower:
                found.append(word)

        if not found:
            return 10.0, found

        # Penalidade por palavra proibida
        penalty = len(found) * 2.5
        score = max(0, 10 - penalty)

        return round(score, 2), found

    @staticmethod
    def _score_quality(response: str) -> Tuple[float, List[str]]:
        """
        Avalia qualidade geral da resposta.

        Criterios:
        - Tamanho adequado (nao muito curta nem muito longa)
        - Nao vazia
        - Sem caracteres estranhos
        """
        issues = []
        score = 10.0

        # Resposta vazia
        if not response or not response.strip():
            return 0.0, ["Resposta vazia"]

        # Muito curta (menos de 20 caracteres)
        if len(response) < 20:
            score -= 3
            issues.append("Resposta muito curta")

        # Muito longa (mais de 3000 caracteres)
        if len(response) > 3000:
            score -= 1
            issues.append("Resposta muito longa")

        # Contem apenas pontuacao ou caracteres especiais
        alpha_count = sum(1 for c in response if c.isalpha())
        if alpha_count < 10:
            score -= 2
            issues.append("Resposta com pouco conteudo textual")

        return max(0, score), issues

    @staticmethod
    def get_status_from_score(score: float) -> str:
        """Retorna status baseado na nota"""
        if score >= 9:
            return "success"
        elif score >= 5:
            return "warning"
        return "error"

    @staticmethod
    def get_status_color(score: float) -> str:
        """Retorna cor CSS baseada na nota"""
        if score >= 9:
            return "#10b981"  # Verde
        elif score >= 5:
            return "#f59e0b"  # Laranja
        return "#ef4444"  # Vermelho
