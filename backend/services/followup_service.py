"""
Servico de Follow-up Automatico

Gerencia o agendamento e envio de mensagens de follow-up automaticas
quando o cliente nao responde apos um periodo configurado.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
import logging

from backend.models.followup import FollowUpJob
from backend.models.ai_config import AIConfig
from backend.models.ai_conversation import AIConversation
from backend.models.client import Client
from backend.services.chatwoot_service import ChatwootService
from backend.services.ai_service import AIService

logger = logging.getLogger(__name__)


class FollowUpService:
    """Servico para gerenciar follow-ups automaticos"""

    @staticmethod
    async def schedule_followup(
        db: AsyncSession,
        client_slug: str,
        conversation_id: int,
        contact_phone: Optional[str],
        ai_config: AIConfig
    ) -> Optional[FollowUpJob]:
        """
        Agenda proximo follow-up apos a IA responder.

        Verifica se follow-up esta habilitado e se ainda nao atingiu o limite.
        """
        if not ai_config.followup_enabled:
            return None

        max_count = ai_config.followup_max_count or 3
        delay_hours = ai_config.followup_delay_hours or 24
        delay_minutes = ai_config.followup_delay_minutes or 0

        # Verificar quantos follow-ups ja foram agendados/enviados para esta conversa
        result = await db.execute(
            select(FollowUpJob)
            .where(
                and_(
                    FollowUpJob.client_slug == client_slug,
                    FollowUpJob.conversation_id == conversation_id,
                    FollowUpJob.status.in_(["pending", "sent"])
                )
            )
            .order_by(FollowUpJob.followup_number.desc())
        )
        existing_jobs = result.scalars().all()

        # Contar apenas os enviados para determinar proximo numero
        sent_count = sum(1 for j in existing_jobs if j.status == "sent")

        if sent_count >= max_count:
            logger.info(f"[{client_slug}] Limite de follow-ups atingido ({sent_count}/{max_count})")
            return None

        # Se ja tem follow-up pendente, nao agendar outro
        pending_jobs = [j for j in existing_jobs if j.status == "pending"]
        if pending_jobs:
            logger.debug(f"[{client_slug}] Follow-up pendente existe, nao agendando outro")
            return None

        # Calcular quando enviar
        scheduled_at = datetime.utcnow() + timedelta(hours=delay_hours, minutes=delay_minutes)

        # Criar job
        job = FollowUpJob(
            client_slug=client_slug,
            conversation_id=conversation_id,
            contact_phone=contact_phone,
            followup_number=sent_count + 1,
            scheduled_at=scheduled_at,
            status="pending"
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)

        logger.info(
            f"[{client_slug}] Follow-up #{job.followup_number} agendado para "
            f"{scheduled_at.strftime('%Y-%m-%d %H:%M')} (conversa {conversation_id})"
        )

        return job

    @staticmethod
    async def cancel_pending_followups(
        db: AsyncSession,
        client_slug: str,
        conversation_id: int,
        reason: str = "client_responded"
    ) -> int:
        """
        Cancela todos os follow-ups pendentes de uma conversa.

        Chamado quando o cliente responde ou a conversa e transferida.
        """
        result = await db.execute(
            update(FollowUpJob)
            .where(
                and_(
                    FollowUpJob.client_slug == client_slug,
                    FollowUpJob.conversation_id == conversation_id,
                    FollowUpJob.status == "pending"
                )
            )
            .values(
                status="cancelled",
                cancelled_reason=reason,
                updated_at=datetime.utcnow()
            )
            .returning(FollowUpJob.id)
        )
        cancelled_ids = result.fetchall()
        await db.commit()

        count = len(cancelled_ids)
        if count > 0:
            logger.info(f"[{client_slug}] {count} follow-up(s) cancelado(s): {reason}")

        return count

    @staticmethod
    async def get_due_jobs(db: AsyncSession, limit: int = 100) -> List[FollowUpJob]:
        """
        Busca jobs que devem ser processados agora.

        Retorna jobs com status=pending e scheduled_at <= now.
        """
        now = datetime.utcnow()
        result = await db.execute(
            select(FollowUpJob)
            .where(
                and_(
                    FollowUpJob.status == "pending",
                    FollowUpJob.scheduled_at <= now
                )
            )
            .order_by(FollowUpJob.scheduled_at)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def should_send_followup(
        chatwoot: ChatwootService,
        conversation_id: int,
        ai_config: AIConfig
    ) -> Tuple[bool, str]:
        """
        Verifica se o follow-up deve ser enviado.

        Condicoes:
        1. Ultima mensagem foi da IA (outgoing)
        2. Conversa ainda esta atribuida ao agente de IA configurado

        Returns:
            Tuple[bool, str]: (deve_enviar, motivo)
        """
        try:
            # Buscar conversa no Chatwoot
            conv = await chatwoot.get_conversation(conversation_id)

            # Verificar assignee
            if ai_config.required_assignee_name:
                meta = conv.get("meta", {})
                assignee = meta.get("assignee") or conv.get("assignee") or {}
                assignee_name = assignee.get("name", "") if isinstance(assignee, dict) else ""

                if assignee_name.lower() != ai_config.required_assignee_name.lower():
                    return False, "transferred_to_human"

            # Buscar mensagens
            messages_data = await chatwoot.get_conversation_messages(conversation_id)
            messages = messages_data.get("payload", []) if isinstance(messages_data, dict) else messages_data

            if not messages:
                return False, "no_messages"

            # Verificar ultima mensagem
            # Mensagens vem ordenadas por created_at, a mais recente no final
            last_msg = messages[-1] if messages else None

            if not last_msg:
                return False, "no_messages"

            # message_type: 0=incoming (cliente), 1=outgoing (agente/IA)
            msg_type = last_msg.get("message_type")
            if msg_type == 0 or msg_type == "incoming":
                return False, "client_responded"

            return True, "ok"

        except Exception as e:
            logger.error(f"Erro ao verificar condicoes de follow-up: {e}")
            return False, f"error: {str(e)}"

    @staticmethod
    async def generate_followup_message(
        ai_config: AIConfig,
        conversation_history: List[Dict],
        followup_number: int,
        max_followups: int
    ) -> str:
        """
        Gera mensagem de follow-up usando IA.

        Analisa o historico da conversa e gera uma mensagem contextualizada.
        """
        # Se tem template configurado, usar ele
        if ai_config.followup_message_template:
            return ai_config.followup_message_template

        # Formatar historico para o prompt
        history_text = ""
        for msg in conversation_history[-10:]:  # Ultimas 10 mensagens
            role = "Cliente" if msg.get("role") == "user" else "Assistente"
            content = msg.get("content", "")[:200]  # Limitar tamanho
            history_text += f"{role}: {content}\n"

        is_last = followup_number >= max_followups

        prompt = f"""Voce e um assistente de vendas. Gere uma mensagem de follow-up natural e contextualizada.

Historico da conversa:
{history_text}

Este e o follow-up numero {followup_number} de {max_followups}.

Regras:
- Seja breve e direto (maximo 2-3 frases)
- Mencione algo especifico da conversa anterior
- Nao seja invasivo ou insistente
- Use tom amigavel e profissional
- NAO use saudacoes formais (ola, bom dia, etc)
- NAO use emojis em excesso (maximo 1)
{"- Como e o ultimo follow-up, deixe claro que esta a disposicao caso precise" if is_last else "- Ofereca ajuda ou pergunte se ainda tem interesse"}

Gere apenas a mensagem, sem explicacoes ou prefixos."""

        try:
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                api_key=ai_config.api_key,
                model=ai_config.model or "gpt-4o-mini",
                temperature=0.7
            )

            response = await llm.ainvoke(prompt)
            return response.content.strip()

        except Exception as e:
            logger.error(f"Erro ao gerar mensagem de follow-up: {e}")
            # Mensagem fallback
            if is_last:
                return "Oi! So passando para dizer que estou a disposicao se precisar de qualquer ajuda. E so me chamar! 😊"
            else:
                return "Oi! Vi que ficou de analisar algumas opcoes. Posso ajudar com mais informacoes?"

    @staticmethod
    async def process_job(db: AsyncSession, job: FollowUpJob) -> bool:
        """
        Processa um job de follow-up.

        1. Busca configuracoes do cliente
        2. Verifica se deve enviar
        3. Gera mensagem
        4. Envia via Chatwoot
        5. Atualiza status do job
        6. Agenda proximo follow-up se necessario

        Returns:
            bool: True se enviou com sucesso
        """
        try:
            # Buscar cliente
            result = await db.execute(
                select(Client).where(Client.slug == job.client_slug)
            )
            client = result.scalar_one_or_none()

            if not client:
                job.status = "failed"
                job.error_message = "Cliente nao encontrado"
                await db.commit()
                return False

            # Buscar config de IA
            result = await db.execute(
                select(AIConfig).where(AIConfig.client_slug == job.client_slug)
            )
            ai_config = result.scalar_one_or_none()

            if not ai_config or not ai_config.enabled:
                job.status = "cancelled"
                job.cancelled_reason = "ai_disabled"
                await db.commit()
                return False

            if not ai_config.followup_enabled:
                job.status = "cancelled"
                job.cancelled_reason = "followup_disabled"
                await db.commit()
                return False

            # Criar servico Chatwoot
            chatwoot = ChatwootService(
                base_url=client.chatwoot_url,
                api_token=client.api_token,
                account_id=client.account_id
            )

            # Verificar condicoes
            should_send, reason = await FollowUpService.should_send_followup(
                chatwoot=chatwoot,
                conversation_id=job.conversation_id,
                ai_config=ai_config
            )

            if not should_send:
                job.status = "cancelled"
                job.cancelled_reason = reason
                await db.commit()
                logger.info(f"[{job.client_slug}] Follow-up cancelado: {reason}")
                return False

            # Buscar historico da conversa
            result = await db.execute(
                select(AIConversation).where(
                    and_(
                        AIConversation.client_slug == job.client_slug,
                        AIConversation.conversation_id == job.conversation_id
                    )
                )
            )
            ai_conv = result.scalar_one_or_none()
            conversation_history = ai_conv.messages if ai_conv else []

            # Gerar mensagem
            max_count = ai_config.followup_max_count or 3
            message = await FollowUpService.generate_followup_message(
                ai_config=ai_config,
                conversation_history=conversation_history,
                followup_number=job.followup_number,
                max_followups=max_count
            )

            # Enviar mensagem
            await chatwoot.send_message(
                conversation_id=job.conversation_id,
                content=message
            )

            # Atualizar job
            job.status = "sent"
            job.sent_at = datetime.utcnow()
            job.message_sent = message[:2000]  # Limitar tamanho

            # Atualizar historico da conversa
            if ai_conv:
                messages = list(ai_conv.messages or [])
                messages.append({"role": "assistant", "content": message})
                ai_conv.messages = messages
                from sqlalchemy.orm.attributes import flag_modified
                flag_modified(ai_conv, 'messages')

            await db.commit()

            logger.info(
                f"[{job.client_slug}] Follow-up #{job.followup_number} enviado "
                f"(conversa {job.conversation_id})"
            )

            # Agendar proximo follow-up se nao atingiu limite
            if job.followup_number < max_count:
                await FollowUpService.schedule_followup(
                    db=db,
                    client_slug=job.client_slug,
                    conversation_id=job.conversation_id,
                    contact_phone=job.contact_phone,
                    ai_config=ai_config
                )

            return True

        except Exception as e:
            logger.error(f"Erro ao processar follow-up {job.id}: {e}", exc_info=True)
            job.status = "failed"
            job.error_message = str(e)[:500]
            await db.commit()
            return False

    @staticmethod
    async def get_pending_followups(
        db: AsyncSession,
        client_slug: str,
        limit: int = 50
    ) -> List[FollowUpJob]:
        """Lista follow-ups pendentes de um cliente"""
        result = await db.execute(
            select(FollowUpJob)
            .where(
                and_(
                    FollowUpJob.client_slug == client_slug,
                    FollowUpJob.status == "pending"
                )
            )
            .order_by(FollowUpJob.scheduled_at)
            .limit(limit)
        )
        return result.scalars().all()

    @staticmethod
    async def get_followup_stats(
        db: AsyncSession,
        client_slug: str
    ) -> Dict:
        """Retorna estatisticas de follow-ups do cliente"""
        from sqlalchemy import func

        # Total por status
        result = await db.execute(
            select(
                FollowUpJob.status,
                func.count(FollowUpJob.id)
            )
            .where(FollowUpJob.client_slug == client_slug)
            .group_by(FollowUpJob.status)
        )
        status_counts = {row[0]: row[1] for row in result.fetchall()}

        # Pendentes para proximas 24h
        next_24h = datetime.utcnow() + timedelta(hours=24)
        result = await db.execute(
            select(func.count(FollowUpJob.id))
            .where(
                and_(
                    FollowUpJob.client_slug == client_slug,
                    FollowUpJob.status == "pending",
                    FollowUpJob.scheduled_at <= next_24h
                )
            )
        )
        pending_24h = result.scalar() or 0

        return {
            "pending": status_counts.get("pending", 0),
            "sent": status_counts.get("sent", 0),
            "cancelled": status_counts.get("cancelled", 0),
            "failed": status_counts.get("failed", 0),
            "pending_next_24h": pending_24h
        }
