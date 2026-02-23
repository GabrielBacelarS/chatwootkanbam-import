from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from backend.core.config import settings
from backend.core.database import init_db, engine
from backend.core.http_client import get_http_client, close_http_client
from backend.api.routes import api_router
from backend.api.routes.webhook import router as webhook_router

# Silenciar logs verbosos ANTES de configurar o basicConfig
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("hpack").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)
logging.getLogger("langchain").setLevel(logging.WARNING)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação"""
    # Startup
    logger.info(f"Iniciando {settings.app_name} v{settings.version}")
    await init_db()
    logger.info("Banco de dados inicializado")
    get_http_client()  # Inicializa pool de conexões HTTP
    logger.info("Pool de conexões HTTP inicializado")
    yield
    # Shutdown
    await close_http_client()
    await engine.dispose()
    logger.info("Aplicação encerrada")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Sistema de IA/RAG integrado com Chatwoot",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handler global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Erro não tratado: {exc}", exc_info=True)
    # Em produção, não expor detalhes do erro para evitar vazamento de informações sensíveis
    error_detail = str(exc) if settings.debug else "Entre em contato com o suporte"
    return JSONResponse(
        status_code=500,
        content={"error": "Erro interno do servidor", "detail": error_detail}
    )


# Rotas da API
app.include_router(api_router, prefix="/api")

# Webhook na raiz (Chatwoot chama /webhook/{slug})
app.include_router(webhook_router, prefix="/webhook", tags=["webhook"])


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": settings.version}


# Rota raiz
@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
