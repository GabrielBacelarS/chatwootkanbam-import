"""
Worker de Follow-up Automatico

Roda em background verificando e processando follow-ups pendentes.
"""
import asyncio
import logging
from datetime import datetime

from backend.core.database import AsyncSessionLocal
from backend.services.followup_service import FollowUpService

logger = logging.getLogger(__name__)

# Intervalo de verificacao (em segundos)
CHECK_INTERVAL = 60  # 1 minuto


async def followup_worker():
    """
    Worker que roda em background verificando follow-ups.

    - Executa a cada CHECK_INTERVAL segundos
    - Busca jobs pendentes com scheduled_at <= agora
    - Processa cada job verificando condicoes e enviando mensagem
    """
    logger.info("Follow-up worker iniciado")

    while True:
        try:
            async with AsyncSessionLocal() as db:
                # Buscar jobs que devem ser processados
                due_jobs = await FollowUpService.get_due_jobs(db)

                if due_jobs:
                    logger.info(f"Processando {len(due_jobs)} follow-up(s) pendente(s)")

                for job in due_jobs:
                    try:
                        # Processar job em uma sessao separada para isolar transacoes
                        async with AsyncSessionLocal() as job_db:
                            await FollowUpService.process_job(job_db, job)
                    except Exception as e:
                        logger.error(f"Erro ao processar follow-up {job.id}: {e}")

        except Exception as e:
            logger.error(f"Erro no worker de follow-up: {e}", exc_info=True)

        # Aguardar proximo ciclo
        await asyncio.sleep(CHECK_INTERVAL)


async def start_followup_worker():
    """Inicia o worker de follow-up como task em background"""
    task = asyncio.create_task(followup_worker())
    return task


def stop_followup_worker(task: asyncio.Task):
    """Para o worker de follow-up"""
    if task and not task.done():
        task.cancel()
        logger.info("Follow-up worker parado")
