from fastapi import APIRouter
from backend.api.routes import clients, chatwoot_proxy, ai, webhook, products, schemas, batch_testing, analytics, integrations, ab_testing, compliance, lead_scoring

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

# Rotas de analytics
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])

# Rotas de integracoes CRM
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])

# Rotas de A/B Testing
api_router.include_router(ab_testing.router, prefix="/ab-testing", tags=["ab-testing"])

# Rotas de compliance LGPD
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])

# Proxy para Chatwoot (para buscar dados do Chatwoot como inboxes, etc)
api_router.include_router(chatwoot_proxy.router, tags=["chatwoot"])

# Rotas de Lead Scoring
api_router.include_router(lead_scoring.router, prefix="/lead-scoring", tags=["lead-scoring"])
