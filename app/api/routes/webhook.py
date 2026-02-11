from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from typing import Optional
from app.core.database import get_db, AsyncSessionLocal
from app.models import Client, AIConfig, AIKnowledgeFile, AIConversation
from app.services import AIService, ChatwootService, WhisperService

router = APIRouter()
logger = logging.getLogger(__name__)


async def process_webhook(slug: str, payload: dict):
    """Processa webhook do Chatwoot em background"""
    async with AsyncSessionLocal() as db:
        try:
            # Verificar se é mensagem incoming (do cliente)
            message_type = payload.get("message_type")
            if message_type != "incoming":
                logger.info(f"[{slug}] Ignorado: message_type={message_type}")
                return

            # Buscar cliente
            result = await db.execute(select(Client).where(Client.slug == slug))
            client = result.scalar_one_or_none()
            if not client:
                logger.error(f"[{slug}] Cliente não encontrado")
                return

            # Buscar configuração de IA
            result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
            ai_config = result.scalar_one_or_none()

            if not ai_config or not ai_config.enabled:
                logger.info(f"[{slug}] IA desabilitada ou não configurada")
                return

            conversation = payload.get("conversation", {})
            conversation_id = conversation.get("id")
            message = payload.get("content", "")
            attachments = payload.get("attachments", [])

            logger.info(f"[{slug}] Processando mensagem na conversa {conversation_id}")

            # Verificar se só responde não atribuídas
            if ai_config.only_unassigned and conversation.get("assignee_id"):
                logger.info(f"[{slug}] Ignorado: conversa já atribuída")
                return

            # Processar áudio se houver
            for att in attachments:
                if att.get("file_type") == "audio" and att.get("data_url"):
                    logger.info(f"[{slug}] Processando áudio")
                    whisper_key = (
                        ai_config.api_key if ai_config.provider == "openai"
                        else ai_config.openai_key_for_whisper
                    )

                    if whisper_key:
                        audio_data = await WhisperService.download_audio(att["data_url"])
                        if audio_data:
                            transcription = await WhisperService.transcribe_audio(
                                api_key=whisper_key,
                                audio_data=audio_data,
                                mime_type=att.get("content_type", "audio/ogg")
                            )
                            if transcription:
                                message = f"{message}\n[Áudio transcrito]: {transcription}" if message else f"[Áudio transcrito]: {transcription}"
                                logger.info(f"[{slug}] Áudio transcrito: {transcription[:50]}...")
                    else:
                        message = f"{message}\n[Áudio recebido - transcrição não disponível]" if message else "[Áudio recebido]"

            # Ignorar se mensagem vazia
            if not message or not message.strip():
                logger.info(f"[{slug}] Ignorado: mensagem vazia")
                return

            # Verificar palavras de transferência
            lower_message = message.lower()
            transfer_keywords = ai_config.transfer_keywords or []
            if any(kw.lower() in lower_message for kw in transfer_keywords):
                logger.info(f"[{slug}] Transferência solicitada")
                return

            # Buscar/criar histórico da conversa
            result = await db.execute(
                select(AIConversation).where(
                    AIConversation.client_slug == slug,
                    AIConversation.conversation_id == conversation_id
                )
            )
            ai_conv = result.scalar_one_or_none()

            if not ai_conv:
                ai_conv = AIConversation(
                    client_slug=slug,
                    conversation_id=conversation_id,
                    messages=[]
                )
                db.add(ai_conv)

            messages = ai_conv.messages or []
            messages.append({"role": "user", "content": message})

            # Verificar limite de mensagens
            max_messages = (ai_config.max_messages_before_transfer or 10) * 2
            if len(messages) > max_messages:
                logger.info(f"[{slug}] Limite de mensagens atingido")
                return

            # Buscar base de conhecimento
            result = await db.execute(
                select(AIKnowledgeFile).where(AIKnowledgeFile.client_slug == slug)
            )
            files = result.scalars().all()
            knowledge_base = "\n\n".join([f.content for f in files if f.content])

            # Gerar resposta da IA
            logger.info(f"[{slug}] Chamando IA ({ai_config.provider})")
            ai_response = await AIService.generate_response(
                provider=ai_config.provider,
                api_key=ai_config.api_key,
                messages=messages,
                model=ai_config.model,
                system_prompt=ai_config.system_prompt,
                knowledge_base=knowledge_base if knowledge_base else None
            )

            # Adicionar resposta ao histórico
            messages.append({"role": "assistant", "content": ai_response})
            ai_conv.messages = messages
            await db.commit()

            # Dividir mensagem se necessário
            max_length = min(ai_config.split_message_at or 1000, 4000)
            parts = AIService.split_message(
                ai_response,
                max_length=max_length,
                split_by_paragraph=ai_config.split_by_paragraph
            )

            # Enviar resposta(s) para o Chatwoot
            chatwoot = ChatwootService(
                base_url=client.chatwoot_url,
                api_token=client.api_token,
                account_id=client.account_id
            )

            for i, part in enumerate(parts):
                logger.info(f"[{slug}] Enviando parte {i+1}/{len(parts)}")
                await chatwoot.send_message(
                    conversation_id=conversation_id,
                    content=part
                )

            logger.info(f"[{slug}] Resposta enviada com sucesso")

        except Exception as e:
            logger.error(f"[{slug}] Erro no webhook: {e}", exc_info=True)


@router.post("/{slug}/webhook")
async def receive_webhook(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Recebe webhook do Chatwoot"""
    try:
        payload = await request.json()
        logger.info(f"[{slug}] Webhook recebido: event={payload.get('event')}")

        # Processar em background para responder rápido
        background_tasks.add_task(process_webhook, slug, payload)

        return {"status": "received"}

    except Exception as e:
        logger.error(f"[{slug}] Erro ao receber webhook: {e}")
        return {"status": "error", "message": str(e)}
