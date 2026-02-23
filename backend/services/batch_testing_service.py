"""
Servico de execucao de testes em lote para agentes IA
Executa multiplos testes em paralelo com rate limiting
"""
import asyncio
import time
from asyncio import Semaphore
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
import logging

from backend.models.ai_test_case import AITestCase
from backend.models.ai_test_run import AITestRun, AITestResult
from backend.models.ai_config import AIConfig
from backend.services.test_scoring_service import TestScoringService
from backend.services.sales_agent_service import run_sales_agent

logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter simples baseado em token bucket"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self.timestamps: List[float] = []
        self.lock = asyncio.Lock()

    async def acquire(self):
        """Aguarda ate ter permissao para executar"""
        async with self.lock:
            now = time.time()

            # Remove timestamps antigos
            self.timestamps = [t for t in self.timestamps if now - t < self.window]

            # Se atingiu o limite, aguarda
            while len(self.timestamps) >= self.max_requests:
                wait_time = self.window - (now - self.timestamps[0])
                logger.info(f"[RateLimiter] Aguardando {wait_time:.1f}s (limite atingido)")
                await asyncio.sleep(max(0.1, wait_time))
                now = time.time()
                self.timestamps = [t for t in self.timestamps if now - t < self.window]

            self.timestamps.append(now)


class BatchTestingService:
    """Servico para execucao de testes em lote com controle de concorrencia"""

    # Custos estimados por 1000 tokens (USD)
    COST_PER_1K_TOKENS = {
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gemini-1.5-flash": {"input": 0.000075, "output": 0.0003},
        "gemini-1.5-pro": {"input": 0.00125, "output": 0.005}
    }

    def __init__(self, rate_limit: int = 60):
        self.rate_limiter = RateLimiter(max_requests=rate_limit, window_seconds=60)

    async def run_batch(
        self,
        test_cases: List[AITestCase],
        ai_config: AIConfig,
        products: List[Dict],
        concurrent_limit: int = 10,
        progress_callback: Optional[Callable] = None,
        schema: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Executa multiplos casos de teste em paralelo.

        Args:
            test_cases: Lista de casos de teste
            ai_config: Configuracao do agente IA
            products: Lista de produtos disponiveis
            concurrent_limit: Limite de execucoes simultaneas (10, 15 ou 20)
            progress_callback: Callback para reportar progresso
            schema: Schema de produto (opcional)

        Returns:
            Dict com resultados agregados e lista de resultados individuais
        """
        # Semaforo para controle de concorrencia
        semaphore = Semaphore(concurrent_limit)

        start_time = time.time()
        completed = 0
        results: List[AITestResult] = []

        async def run_single_test(test_case: AITestCase, index: int) -> AITestResult:
            nonlocal completed

            async with semaphore:
                await self.rate_limiter.acquire()

                try:
                    result = await self._execute_test(
                        test_case=test_case,
                        ai_config=ai_config,
                        products=products,
                        schema=schema
                    )

                    completed += 1

                    if progress_callback:
                        await progress_callback(completed, len(test_cases), result)

                    logger.info(
                        f"[BatchTest] {completed}/{len(test_cases)} - "
                        f"'{test_case.name}' -> Score: {result.score:.1f}"
                    )

                    return result

                except Exception as e:
                    logger.error(f"[BatchTest] Erro no teste '{test_case.name}': {e}")
                    completed += 1

                    return AITestResult(
                        test_case_id=test_case.id,
                        ai_response=f"Erro de execucao: {str(e)}",
                        tools_used=[],
                        execution_time_ms=0,
                        score=0.0,
                        score_breakdown={"error": str(e)},
                        issues=[f"Erro de execucao: {str(e)}"]
                    )

        # Executar todos os testes em paralelo (respeitando limites)
        logger.info(f"[BatchTest] Iniciando {len(test_cases)} testes (concurrent={concurrent_limit})")

        tasks = [
            run_single_test(tc, i)
            for i, tc in enumerate(test_cases)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Calcular metricas agregadas
        total_time = int((time.time() - start_time) * 1000)

        valid_results = [r for r in results if isinstance(r, AITestResult)]
        scores = [r.score for r in valid_results if r.score is not None]

        passed = sum(1 for s in scores if s >= 9)
        warning = sum(1 for s in scores if 5 <= s < 9)
        failed = sum(1 for s in scores if s < 5)
        avg_score = sum(scores) / len(scores) if scores else 0

        # Calcular custo estimado
        total_tokens_input = sum(r.tokens_input or 0 for r in valid_results)
        total_tokens_output = sum(r.tokens_output or 0 for r in valid_results)
        estimated_cost = self._estimate_cost(
            ai_config.model,
            total_tokens_input,
            total_tokens_output
        )

        logger.info(
            f"[BatchTest] Concluido! "
            f"Passed: {passed}, Warning: {warning}, Failed: {failed}, "
            f"Avg: {avg_score:.2f}, Time: {total_time}ms"
        )

        return {
            "results": valid_results,
            "passed_count": passed,
            "warning_count": warning,
            "failed_count": failed,
            "average_score": round(avg_score, 2),
            "total_execution_time_ms": total_time,
            "total_tokens_used": total_tokens_input + total_tokens_output,
            "estimated_cost": round(estimated_cost, 4)
        }

    async def _execute_test(
        self,
        test_case: AITestCase,
        ai_config: AIConfig,
        products: List[Dict],
        schema: Optional[Dict] = None
    ) -> AITestResult:
        """Executa um caso de teste individual"""
        start = time.time()

        # Executar agente
        result = await run_sales_agent(
            message=test_case.input_message,
            messages_history=[],  # Conversa limpa
            system_prompt=ai_config.system_prompt or "Voce e um assistente de vendas.",
            products=products,
            api_key=ai_config.api_key,
            model=ai_config.model,
            conversation_id=0,  # Modo teste
            client_slug=test_case.client_slug,
            chatwoot_service=None,  # Nao envia mensagens reais
            schema=schema,
            enabled_tools=ai_config.enabled_tools,
            product_keywords=ai_config.product_keywords
        )

        execution_time = int((time.time() - start) * 1000)

        ai_response = result.get("response", "")
        tools_used = result.get("tools_used", [])

        # Calcular pontuacao
        score, breakdown, issues = TestScoringService.calculate_score(
            input_message=test_case.input_message,
            ai_response=ai_response,
            tools_used=tools_used,
            expected_tools=test_case.expected_tools,
            expected_keywords=test_case.expected_keywords,
            should_not_contain=test_case.should_not_contain,
            weight_tools=test_case.weight_tools,
            weight_keywords=test_case.weight_keywords,
            weight_no_errors=test_case.weight_no_errors,
            weight_quality=test_case.weight_quality
        )

        # Estimar tokens (aproximacao)
        tokens_input = len(test_case.input_message.split()) * 1.3
        tokens_output = len(ai_response.split()) * 1.3

        return AITestResult(
            test_case_id=test_case.id,
            ai_response=ai_response,
            tools_used=tools_used,
            execution_time_ms=execution_time,
            score=score,
            score_breakdown=breakdown,
            issues=issues,
            tokens_input=int(tokens_input),
            tokens_output=int(tokens_output)
        )

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Estima custo em USD baseado no modelo e tokens"""
        rates = self.COST_PER_1K_TOKENS.get(model, self.COST_PER_1K_TOKENS["gpt-4o-mini"])

        input_cost = (input_tokens / 1000) * rates["input"]
        output_cost = (output_tokens / 1000) * rates["output"]

        return input_cost + output_cost
