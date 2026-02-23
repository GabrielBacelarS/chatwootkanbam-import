from fastapi import APIRouter
from backend.api.routes import clients, chatwoot_proxy, ai, webhook, products, schemas, batch_testing

api_router = APIRouter()

# Rotas de schemas (superadmin) - ANTES de tudo
api_router.include_router(schemas.router, tags=["schemas"])

# Rotas de clientes
api_router.include_router(clients.router, prefix="/clients", tags=["clients"])

# Rotas de IA
api_router.include_router(ai.router, tags=["ai"])

# Rotas de testes em lote
api_router.include_router(batch_testing.router, tags=["batch-testing"])

# Webhook
api_router.include_router(webhook.router, tags=["webhook"])

# Rotas de produtos/RAG
api_router.include_router(products.router, tags=["products"])

# Proxy para Chatwoot (para buscar dados do Chatwoot como inboxes, etc)
api_router.include_router(chatwoot_proxy.router, tags=["chatwoot"])
