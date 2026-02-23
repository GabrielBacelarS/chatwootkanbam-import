"""
Rate Limiter Service usando Redis
Protege a API contra DDoS e uso excessivo
"""
from typing import Optional, Tuple
from datetime import datetime
import logging
import redis.asyncio as aioredis

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Cliente Redis global
_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Retorna cliente Redis, criando se necessario"""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    return _redis_client


async def close_redis():
    """Fecha conexao Redis"""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


class RateLimiter:
    """
    Rate Limiter usando algoritmo de janela deslizante (sliding window)

    Uso:
        limiter = RateLimiter()
        allowed, info = await limiter.check("webhook:cliente-x", max_requests=100, window=60)
        if not allowed:
            raise HTTPException(429, detail=info)
    """

    def __init__(self):
        self.enabled = settings.rate_limit_enabled

    async def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> Tuple[bool, dict]:
        """
        Verifica se a requisicao esta dentro do limite

        Args:
            key: Identificador unico (ex: "webhook:cliente-slug" ou "ip:192.168.1.1")
            max_requests: Numero maximo de requisicoes permitidas
            window_seconds: Janela de tempo em segundos

        Returns:
            Tuple[bool, dict]: (permitido, info)
            info contém: remaining, reset_at, limit
        """
        if not self.enabled:
            return True, {"remaining": max_requests, "limit": max_requests, "reset_at": 0}

        try:
            redis = await get_redis()
            redis_key = f"ratelimit:{key}"
            now = datetime.now().timestamp()

            # Usar pipeline para atomicidade
            pipe = redis.pipeline()

            # Remover entradas antigas (fora da janela)
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)

            # Contar requisicoes na janela atual
            pipe.zcard(redis_key)

            # Adicionar requisicao atual
            pipe.zadd(redis_key, {str(now): now})

            # Definir TTL para limpeza automatica
            pipe.expire(redis_key, window_seconds + 10)

            results = await pipe.execute()
            current_count = results[1]

            remaining = max(0, max_requests - current_count - 1)
            reset_at = int(now + window_seconds)

            info = {
                "remaining": remaining,
                "limit": max_requests,
                "reset_at": reset_at,
                "current": current_count + 1
            }

            if current_count >= max_requests:
                logger.warning(f"Rate limit excedido para {key}: {current_count}/{max_requests}")
                return False, info

            return True, info

        except Exception as e:
            # Se Redis falhar, permitir a requisicao (fail open)
            logger.error(f"Erro no rate limiter: {e}")
            return True, {"remaining": max_requests, "limit": max_requests, "reset_at": 0, "error": str(e)}

    async def get_usage(self, key: str, window_seconds: int = 60) -> dict:
        """
        Retorna estatisticas de uso para uma chave
        """
        try:
            redis = await get_redis()
            redis_key = f"ratelimit:{key}"
            now = datetime.now().timestamp()

            # Contar requisicoes na janela
            count = await redis.zcount(redis_key, now - window_seconds, now)

            return {
                "key": key,
                "requests_in_window": count,
                "window_seconds": window_seconds
            }
        except Exception as e:
            logger.error(f"Erro ao obter uso: {e}")
            return {"error": str(e)}

    async def reset(self, key: str) -> bool:
        """
        Reseta o contador para uma chave
        """
        try:
            redis = await get_redis()
            redis_key = f"ratelimit:{key}"
            await redis.delete(redis_key)
            return True
        except Exception as e:
            logger.error(f"Erro ao resetar rate limit: {e}")
            return False


# Instancia global
rate_limiter = RateLimiter()


# Helpers para casos de uso comuns
async def check_webhook_rate_limit(client_slug: str) -> Tuple[bool, dict]:
    """Verifica rate limit para webhooks de um cliente"""
    return await rate_limiter.check(
        key=f"webhook:{client_slug}",
        max_requests=settings.rate_limit_webhook_per_minute,
        window_seconds=60
    )


async def check_api_rate_limit(ip_address: str) -> Tuple[bool, dict]:
    """Verifica rate limit para API geral por IP"""
    return await rate_limiter.check(
        key=f"api:{ip_address}",
        max_requests=settings.rate_limit_requests_per_minute,
        window_seconds=60
    )


async def check_ai_rate_limit(client_slug: str) -> Tuple[bool, dict]:
    """Verifica rate limit para chamadas de IA (mais restritivo)"""
    return await rate_limiter.check(
        key=f"ai:{client_slug}",
        max_requests=settings.rate_limit_ai_per_minute,
        window_seconds=60
    )
