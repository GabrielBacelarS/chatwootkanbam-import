"""
Testes para servico de rate limiting
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


def create_pipeline_mock(execute_return_value):
    """Cria mock do pipeline do Redis"""
    pipeline = MagicMock()
    # Metodos de pipeline retornam o proprio pipeline para encadeamento
    pipeline.zremrangebyscore.return_value = pipeline
    pipeline.zcard.return_value = pipeline
    pipeline.zadd.return_value = pipeline
    pipeline.expire.return_value = pipeline
    # Execute e async
    pipeline.execute = AsyncMock(return_value=execute_return_value)
    return pipeline


@pytest.mark.asyncio
async def test_rate_limit_allows_request():
    """Testa que requisicoes dentro do limite sao permitidas"""
    from backend.core.rate_limiter import RateLimiter

    limiter = RateLimiter()
    limiter.enabled = True

    with patch("backend.core.rate_limiter.get_redis", new_callable=AsyncMock) as mock_get_redis:
        redis_mock = MagicMock()

        # Pipeline que retorna contagem = 1 (abaixo do limite)
        pipeline = create_pipeline_mock([0, 1, 1, True])
        redis_mock.pipeline.return_value = pipeline

        mock_get_redis.return_value = redis_mock

        allowed, info = await limiter.check("test:key", max_requests=10)

        assert allowed == True
        assert info["remaining"] >= 0
        assert info["limit"] == 10


@pytest.mark.asyncio
async def test_rate_limit_blocks_request():
    """Testa que requisicoes acima do limite sao bloqueadas"""
    from backend.core.rate_limiter import RateLimiter

    limiter = RateLimiter()
    limiter.enabled = True

    with patch("backend.core.rate_limiter.get_redis", new_callable=AsyncMock) as mock_get_redis:
        redis_mock = MagicMock()

        # Pipeline que retorna contagem = 100 (acima do limite de 10)
        pipeline = create_pipeline_mock([0, 100, 1, True])
        redis_mock.pipeline.return_value = pipeline

        mock_get_redis.return_value = redis_mock

        allowed, info = await limiter.check("test:key", max_requests=10)

        assert allowed == False
        assert info["remaining"] == 0


@pytest.mark.asyncio
async def test_rate_limit_disabled():
    """Testa que rate limiting desabilitado permite tudo"""
    from backend.core.rate_limiter import RateLimiter

    limiter = RateLimiter()
    limiter.enabled = False

    allowed, info = await limiter.check("test:key", max_requests=1)

    assert allowed == True


@pytest.mark.asyncio
async def test_rate_limit_fails_open():
    """Testa que falha no Redis permite a requisicao (fail open)"""
    from backend.core.rate_limiter import RateLimiter

    limiter = RateLimiter()
    limiter.enabled = True

    with patch("backend.core.rate_limiter.get_redis") as mock_get_redis:
        # Simular erro no Redis
        mock_get_redis.side_effect = Exception("Redis connection error")

        allowed, info = await limiter.check("test:key", max_requests=10)

        # Deve permitir mesmo com erro (fail open)
        assert allowed == True
        assert "error" in info


@pytest.mark.asyncio
async def test_webhook_rate_limit_helper():
    """Testa helper de rate limit para webhooks"""
    from backend.core.rate_limiter import check_webhook_rate_limit

    with patch("backend.core.rate_limiter.rate_limiter.check") as mock_check:
        mock_check.return_value = (True, {"remaining": 99})

        allowed, info = await check_webhook_rate_limit("test-client")

        mock_check.assert_called_once()
        assert "webhook:test-client" in str(mock_check.call_args)


@pytest.mark.asyncio
async def test_ai_rate_limit_helper():
    """Testa helper de rate limit para IA"""
    from backend.core.rate_limiter import check_ai_rate_limit

    with patch("backend.core.rate_limiter.rate_limiter.check") as mock_check:
        mock_check.return_value = (True, {"remaining": 29})

        allowed, info = await check_ai_rate_limit("test-client")

        mock_check.assert_called_once()
        assert "ai:test-client" in str(mock_check.call_args)
