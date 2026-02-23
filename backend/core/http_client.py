import httpx
from contextlib import asynccontextmanager

# Cliente HTTP global com pool de conexões
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Retorna o cliente HTTP global"""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0
            ),
            http2=True  # HTTP/2 para melhor performance
        )
    return _http_client


async def close_http_client():
    """Fecha o cliente HTTP"""
    global _http_client
    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None


async def startup_http_client():
    """Inicializa o cliente HTTP no startup"""
    get_http_client()


@asynccontextmanager
async def lifespan_http_client():
    """Context manager para lifespan do FastAPI"""
    get_http_client()
    yield
    await close_http_client()
