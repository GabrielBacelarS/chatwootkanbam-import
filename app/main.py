from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

from app.core.config import settings
from app.core.database import init_db, engine
from app.api.routes import api_router
from app.api.routes.pages import router as pages_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
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
    yield
    # Shutdown
    await engine.dispose()
    logger.info("Aplicação encerrada")


# Criar aplicação FastAPI
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Sistema de integração Chatwoot com Kanban, IA e Disparador de Mensagens",
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
    return JSONResponse(
        status_code=500,
        content={"error": "Erro interno do servidor", "detail": str(exc)}
    )


# Rotas da API
app.include_router(api_router, prefix="/api")

# Rotas de páginas HTML
app.include_router(pages_router)


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
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
