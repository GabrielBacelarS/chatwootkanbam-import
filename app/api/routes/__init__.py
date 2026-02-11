from fastapi import APIRouter
from app.api.routes import clients, chatwoot_proxy, ai, webhook

api_router = APIRouter()

# Rotas de clientes
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])

# Rotas de IA
api_router.include_router(ai.router, tags=["ai"])

# Webhook
api_router.include_router(webhook.router, tags=["webhook"])

# Proxy para Chatwoot (mantém compatibilidade com rotas existentes)
api_router.include_router(chatwoot_proxy.router, tags=["chatwoot"])
