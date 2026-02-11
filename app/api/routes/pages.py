from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import os
from app.core.database import get_db
from app.models import Client

router = APIRouter()

# Diretório base do projeto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


async def get_client_config(slug: str, db: AsyncSession) -> dict:
    """Obtém configuração do cliente para injetar no HTML"""
    result = await db.execute(select(Client).where(Client.slug == slug))
    client = result.scalar_one_or_none()
    if client:
        return {
            "slug": client.slug,
            "name": client.name,
            "chatwootUrl": client.chatwoot_url,
            "accountId": client.account_id
        }
    return {}


def inject_config(html_content: str, config: dict, request: Request) -> str:
    """Injeta configuração do cliente no HTML"""
    # Determinar base URL
    host = request.headers.get("host", "localhost:3000")
    protocol = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
    base_url = f"{protocol}://{host}"

    config_with_base = {**config, "baseUrl": base_url}
    config_script = f"<script>window.CLIENT_CONFIG = {config_with_base};</script>"

    # Injetar antes do </head>
    if "</head>" in html_content:
        html_content = html_content.replace("</head>", f"{config_script}\n</head>")

    return html_content


@router.get("/kanban/{slug}", response_class=HTMLResponse)
async def kanban_page(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Página do Kanban"""
    config = await get_client_config(slug, db)
    if not config:
        return HTMLResponse("<h1>Cliente não encontrado</h1>", status_code=404)

    kanban_path = os.path.join(BASE_DIR, "kanban.html")
    if not os.path.exists(kanban_path):
        return HTMLResponse("<h1>Página não encontrada</h1>", status_code=404)

    with open(kanban_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(inject_config(html_content, config, request))


@router.get("/ia/{slug}", response_class=HTMLResponse)
async def ia_page(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Página de configuração de IA"""
    config = await get_client_config(slug, db)
    if not config:
        return HTMLResponse("<h1>Cliente não encontrado</h1>", status_code=404)

    ia_path = os.path.join(BASE_DIR, "ia.html")
    if not os.path.exists(ia_path):
        return HTMLResponse("<h1>Página não encontrada</h1>", status_code=404)

    with open(ia_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(inject_config(html_content, config, request))


@router.get("/disparador/{slug}", response_class=HTMLResponse)
async def disparador_page(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Página do Disparador de Mensagens"""
    config = await get_client_config(slug, db)
    if not config:
        return HTMLResponse("<h1>Cliente não encontrado</h1>", status_code=404)

    disparador_path = os.path.join(BASE_DIR, "disparador.html")
    if not os.path.exists(disparador_path):
        return HTMLResponse("<h1>Página não encontrada</h1>", status_code=404)

    with open(disparador_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    return HTMLResponse(inject_config(html_content, config, request))


# Removida rota /{slug} para evitar conflito com /health e /docs
