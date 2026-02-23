"""
Rate Limit Middleware para FastAPI
Adiciona headers de rate limit e bloqueia requisicoes excessivas
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging

from backend.core.config import settings
from backend.core.rate_limiter import rate_limiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware que aplica rate limiting em todas as requisicoes

    Headers adicionados:
    - X-RateLimit-Limit: Limite maximo de requisicoes
    - X-RateLimit-Remaining: Requisicoes restantes
    - X-RateLimit-Reset: Timestamp de reset
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    def _get_client_ip(self, request: Request) -> str:
        """Extrai IP do cliente considerando proxies"""
        # Verificar headers de proxy reverso
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback para IP direto
        if request.client:
            return request.client.host

        return "unknown"

    def _get_rate_limit_key(self, request: Request) -> tuple[str, int]:
        """
        Determina a chave e limite baseado no tipo de requisicao

        Returns:
            Tuple[key, max_requests]
        """
        path = request.url.path
        ip = self._get_client_ip(request)

        # Webhook tem limite proprio por cliente
        if path.startswith("/webhook/"):
            # Extrair slug do path
            parts = path.split("/")
            if len(parts) >= 3:
                slug = parts[2]
                return f"webhook:{slug}", settings.rate_limit_webhook_per_minute

        # Endpoints de IA tem limite mais restritivo
        if "/ai-test" in path or "/ai-config" in path:
            return f"ai:{ip}", settings.rate_limit_ai_per_minute

        # API geral por IP
        return f"api:{ip}", settings.rate_limit_requests_per_minute

    async def dispatch(self, request: Request, call_next) -> Response:
        # Pular rate limit se desabilitado
        if not settings.rate_limit_enabled:
            return await call_next(request)

        # Pular health check e docs
        path = request.url.path
        if path in ["/health", "/", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)

        # Verificar rate limit
        key, max_requests = self._get_rate_limit_key(request)
        allowed, info = await rate_limiter.check(key, max_requests)

        if not allowed:
            logger.warning(
                f"Rate limit bloqueado: {key} - "
                f"{info.get('current', 0)}/{info.get('limit', 0)} requisicoes"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Too Many Requests",
                    "detail": f"Rate limit excedido. Tente novamente em {info.get('reset_at', 60) - int(__import__('time').time())} segundos.",
                    "limit": info.get("limit"),
                    "reset_at": info.get("reset_at")
                },
                headers={
                    "X-RateLimit-Limit": str(info.get("limit", 0)),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(info.get("reset_at", 0)),
                    "Retry-After": str(max(1, info.get("reset_at", 60) - int(__import__('time').time())))
                }
            )

        # Processar requisicao
        response = await call_next(request)

        # Adicionar headers de rate limit
        response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(info.get("reset_at", 0))

        return response
