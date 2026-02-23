#!/usr/bin/env python3
"""Script para executar a aplicação localmente"""

import uvicorn
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente
load_dotenv()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    host = os.getenv("HOST", "0.0.0.0")
    debug = os.getenv("DEBUG", "false").lower() == "true"

    print(f"""
    ====================================================
    |   Closefy Kanban Import - FastAPI v2.0.0         |
    ====================================================
    |  Server:  http://{host}:{port}
    |  Docs:    http://{host}:{port}/docs
    |  Health:  http://{host}:{port}/health
    ====================================================
    """)

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=debug,
        log_level="info" if not debug else "debug"
    )
