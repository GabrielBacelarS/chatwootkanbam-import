from fastapi import APIRouter, Depends, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm.attributes import flag_modified
import logging
import asyncio
import time
from datetime import datetime, time as dt_time
from typing import Optional, List, Dict
from backend.core.database import get_db, AsyncSessionLocal
from backend.models import Client, AIConfig, AIKnowledgeFile, AIConversation, Product, ProductSchema
from backend.services import ChatwootService, WhisperService, MinioService, AIService
from backend.services.sales_agent_service import run_sales_agent
from backend.services.analytics_service import AnalyticsService
from backend.core.config import settings

router = APIRouter()
logger = logging.getLogger("IA")


def estimate_tokens(text: str) -> int:
    """Estima numero de tokens baseado no texto (aproximacao: 1 token ~ 4 caracteres)"""
    if not text:
        return 0
    return len(text) // 4

# Tempo de espera padrao para agrupar mensagens (em segundos)
# Valor pode ser configurado por cliente em ai_config.debounce_seconds
DEFAULT_DEBOUNCE_SECONDS = 10.0


def is_within_working_hours(ai_config: AIConfig) -> bool:
    """
    Verifica se o momento atual está dentro do horário comercial configurado.
    Retorna True se deve responder, False se fora do horário.
    """
    # Se não tem horário configurado, sempre responde
    if not ai_config.working_hours_start or not ai_config.working_hours_end:
        return True

    now = datetime.now()
    current_time = now.time()
    current_weekday = now.isoweekday()  # 1=segunda, 7=domingo

    # Verificar dia da semana (working_days usa 1-7, isoweekday também)
    working_days = ai_config.working_days or [1, 2, 3, 4, 5]  # Default: seg-sex
    if current_weekday not in working_days:
        return False

    # Verificar horário
    start = ai_config.working_hours_start
    end = ai_config.working_hours_end

    # Converter para time se necessário (pode vir como string do banco)
    if isinstance(start, str):
        h, m, s = map(int, start.split(':'))
        start = dt_time(h, m, s)
    if isinstance(end, str):
        h, m, s = map(int, end.split(':'))
        end = dt_time(h, m, s)

    return start <= current_time <= end


def truncate(text: str, max_len: int = 50) -> str:
    """Trunca texto para exibicao em logs"""
    if not text:
        return ""
    clean = text.replace("<p>", "").replace("</p>", "").replace("\n", " ").strip()
    if len(clean) > max_len:
        return clean[:max_len] + "..."
    return clean


async def store_pending_message(
    db: AsyncSession,
    slug: str,
    conversation_id: int,
    message: str,
    attachments: List[Dict]
) -> AIConversation:
    """Armazena mensagem pendente para processamento posterior (debounce)"""
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
            messages=[],
            pending_messages=[],
            last_message_at=time.time()
        )
        db.add(ai_conv)
        await db.flush()

    # Adicionar mensagem pendente
    pending = list(ai_conv.pending_messages or [])
    pending.append({
        "text": message,
        "attachments": attachments,
        "timestamp": time.time()
    })
    ai_conv.pending_messages = pending
    ai_conv.last_message_at = time.time()
    flag_modified(ai_conv, 'pending_messages')
    await db.commit()

    return ai_conv


async def process_webhook(slug: str, payload: dict):
    """Processa webhook do Chatwoot em background usando LangGraph com debounce"""
    async with AsyncSessionLocal() as db:
        try:
            # Ignorar mensagens outgoing (da IA)
            message_type = payload.get("message_type")
            if message_type != "incoming":
                return

            # Buscar cliente
            result = await db.execute(select(Client).where(Client.slug == slug))
            client = result.scalar_one_or_none()
            if not client:
                logger.error(f"[{slug}] Cliente nao encontrado")
                return

            # Buscar configuracao de IA
            result = await db.execute(select(AIConfig).where(AIConfig.client_slug == slug))
            ai_config = result.scalar_one_or_none()

            if not ai_config or not ai_config.enabled:
                return

            # Verificar horário comercial
            if not is_within_working_hours(ai_config):
                logger.info(f"[{slug}] Fora do horário comercial - ignorando mensagem")
                return

            conversation = payload.get("conversation", {})
            conversation_id = conversation.get("id")
            message = payload.get("content", "") or ""
            attachments = payload.get("attachments") or []  # Garante lista mesmo se null

            # === DEBOUNCE: Armazenar mensagem e esperar ===
            await store_pending_message(db, slug, conversation_id, message, attachments)

            # Usar tempo de debounce configurado pelo cliente (ou padrao)
            debounce_time = ai_config.debounce_seconds if ai_config.debounce_seconds is not None else DEFAULT_DEBOUNCE_SECONDS
            logger.info(f"[{slug}] << Recebido (aguardando {debounce_time}s): \"{truncate(message)}\"")

            # Esperar para agrupar mensagens
            await asyncio.sleep(debounce_time)

            # Recarregar para ver se chegaram mais mensagens
            # Usar FOR UPDATE para evitar processamento duplicado (lock na linha)
            result = await db.execute(
                select(AIConversation)
                .where(
                    AIConversation.client_slug == slug,
                    AIConversation.conversation_id == conversation_id
                )
                .with_for_update(skip_locked=True)  # Pula se outra task ja tem lock
            )
            ai_conv = result.scalar_one_or_none()

            if not ai_conv or not ai_conv.pending_messages:
                return  # Ja foi processado por outra task ou locked

            # Verificar se ainda estamos dentro do debounce
            time_since_last = time.time() - (ai_conv.last_message_at or 0)
            if time_since_last < debounce_time - 0.5:
                # Chegou mensagem recente, outra task vai processar
                logger.info(f"[{slug}] Mensagem recente detectada, aguardando proxima task")
                await db.rollback()  # Liberar lock
                return

            # Pegar todas as mensagens pendentes e limpar ATOMICAMENTE
            pending_messages = list(ai_conv.pending_messages or [])
            if not pending_messages:
                await db.rollback()
                return

            ai_conv.pending_messages = []
            flag_modified(ai_conv, 'pending_messages')
            await db.commit()  # Commit libera o lock e salva pending_messages = []

            logger.info(f"[{slug}] Processando {len(pending_messages)} mensagem(ns) agrupada(s)")

            # Criar instancia do ChatwootService
            chatwoot = ChatwootService(
                base_url=client.chatwoot_url,
                api_token=client.api_token,
                account_id=client.account_id
            )

            # Verificar se IA deve responder apenas quando atribuida a um agente especifico
            if ai_config.required_assignee_name:
                meta = conversation.get("meta", {})
                assignee = meta.get("assignee") or conversation.get("assignee") or {}
                assignee_name = assignee.get("name", "") if isinstance(assignee, dict) else ""

                if not assignee_name:
                    try:
                        ia_agent = await chatwoot.get_agent_by_name(ai_config.required_assignee_name)
                        if ia_agent:
                            await chatwoot.assign_conversation_to_agent(
                                conversation_id=conversation_id,
                                assignee_id=ia_agent["id"]
                            )
                            assignee_name = ai_config.required_assignee_name
                        else:
                            logger.error(f"[{slug}] Agente '{ai_config.required_assignee_name}' nao encontrado")
                            return
                    except Exception as e:
                        logger.error(f"[{slug}] Erro ao atribuir agente: {e}")
                        return

                if assignee_name.lower() != ai_config.required_assignee_name.lower():
                    return

            # Verificar se so responde nao atribuidas
            if not ai_config.required_assignee_name:
                if ai_config.only_unassigned and conversation.get("assignee_id"):
                    return

            # === PROCESSAR MENSAGENS AGRUPADAS ===
            combined_text_parts = []
            image_descriptions = []

            for pending_msg in pending_messages:
                msg_text = pending_msg.get("text", "")
                msg_attachments = pending_msg.get("attachments", [])

                # Processar audio se houver
                for att in msg_attachments:
                    if att.get("file_type") == "audio" and att.get("data_url"):
                        whisper_key = ai_config.api_key if ai_config.provider == "openai" else ai_config.openai_key_for_whisper
                        if whisper_key:
                            audio_data = await WhisperService.download_audio(att["data_url"])
                            if audio_data:
                                transcription = await WhisperService.transcribe_audio(
                                    api_key=whisper_key,
                                    audio_data=audio_data,
                                    mime_type=att.get("content_type", "audio/ogg")
                                )
                                if transcription:
                                    msg_text = f"{msg_text}\n[Audio]: {transcription}" if msg_text else f"[Audio]: {transcription}"
                                    logger.info(f"[{slug}] Audio transcrito: {truncate(transcription)}")

                    # Processar imagem - ANALISAR COM VISION API
                    elif att.get("file_type") == "image" and att.get("data_url"):
                        logger.info(f"[{slug}] Analisando imagem enviada pelo cliente...")
                        try:
                            image_analysis = await AIService.analyze_image(
                                api_key=ai_config.api_key,
                                image_url=att["data_url"],
                                context="produto"
                            )
                            if image_analysis and "nao consegui" not in image_analysis.lower():
                                image_descriptions.append(image_analysis)
                                logger.info(f"[{slug}] Imagem identificada: {image_analysis}")
                        except Exception as e:
                            logger.warning(f"[{slug}] Erro ao analisar imagem: {e}")

                if msg_text and msg_text.strip():
                    combined_text_parts.append(msg_text.strip())

            # Combinar tudo em uma mensagem unica
            combined_message = " ".join(combined_text_parts)

            # Flag para indicar se tem imagem (para nao forcar tool automaticamente)
            has_image = len(image_descriptions) > 0

            # Se tiver analise de imagem, adicionar ao contexto
            if image_descriptions:
                image_context = "\n".join([f"[Imagem enviada: {desc}]" for desc in image_descriptions])
                if combined_message:
                    # Usuario mandou texto + imagem - deixar IA entender contexto
                    combined_message = f"{combined_message}\n{image_context}"
                else:
                    # Usuario mandou so imagem - perguntar o que quer saber
                    combined_message = f"O cliente enviou uma imagem mostrando: {image_context}\nPergunte ao cliente o que ele gostaria de saber sobre esse produto."

            # Ignorar mensagem vazia
            if not combined_message or not combined_message.strip():
                return

            # Usar combined_message como a mensagem final
            message = combined_message
            logger.info(f"[{slug}] Mensagem combinada: \"{truncate(message)}\"")

            # Verificar palavras de transferencia
            lower_message = message.lower()
            transfer_keywords = ai_config.transfer_keywords or []
            if any(kw.lower() in lower_message for kw in transfer_keywords):
                logger.info(f"[{slug}] Transferindo para equipe (palavra-chave detectada)")

                # Gerar resumo da conversa para o atendente (ai_conv ja carregado do debounce)
                if ai_conv and ai_conv.messages:
                    try:
                        summary = await AIService.summarize_conversation(
                            api_key=ai_config.api_key,
                            messages=ai_conv.messages,
                            provider=ai_config.provider,
                            model=ai_config.model
                        )
                        # Enviar resumo como nota privada (cliente nao ve)
                        await chatwoot.send_message(
                            conversation_id=conversation_id,
                            content=f"📋 **RESUMO DA CONVERSA (IA)**\n\n{summary}",
                            private=True
                        )
                        logger.info(f"[{slug}] Resumo enviado como nota privada")
                    except Exception as e:
                        logger.warning(f"[{slug}] Erro ao gerar resumo: {e}")

                if ai_config.transfer_team_id:
                    try:
                        # Primeiro atribuir a equipe
                        await chatwoot.assign_conversation_to_team(
                            conversation_id=conversation_id,
                            team_id=ai_config.transfer_team_id
                        )

                        # Depois fazer round-robin para um agente da equipe
                        team_members = await chatwoot.get_team_members(ai_config.transfer_team_id)
                        if team_members:
                            # Round-robin simples usando conversation_id para distribuir
                            agent_index = conversation_id % len(team_members)
                            selected_agent = team_members[agent_index]
                            agent_id = selected_agent.get("id") or selected_agent.get("user_id")

                            if agent_id:
                                await chatwoot.assign_conversation_to_agent(
                                    conversation_id=conversation_id,
                                    assignee_id=agent_id
                                )
                                logger.info(f"[{slug}] Atribuido ao agente: {selected_agent.get('name', agent_id)}")
                            else:
                                logger.warning(f"[{slug}] Membro da equipe sem ID: {selected_agent}")
                        else:
                            logger.warning(f"[{slug}] Equipe {ai_config.transfer_team_id} sem membros")

                    except Exception as e:
                        logger.error(f"[{slug}] Erro ao transferir: {e}")
                return

            # Usar ai_conv ja carregado do debounce
            messages = list(ai_conv.messages or [])
            messages.append({"role": "user", "content": message})

            # Verificar limite de mensagens
            max_messages = (ai_config.max_messages_before_transfer or 10) * 2
            if len(messages) > max_messages:
                logger.info(f"[{slug}] Limite de mensagens atingido - transferindo para equipe")

                # Enviar mensagem ao cliente informando a transferência
                await chatwoot.send_message(
                    conversation_id=conversation_id,
                    content="Vou transferir você para um de nossos atendentes que poderá ajudá-lo melhor. Um momento, por favor! 😊"
                )

                # Gerar resumo da conversa para o atendente
                if ai_conv and ai_conv.messages:
                    try:
                        summary = await AIService.summarize_conversation(
                            api_key=ai_config.api_key,
                            messages=ai_conv.messages,
                            provider=ai_config.provider,
                            model=ai_config.model
                        )
                        await chatwoot.send_message(
                            conversation_id=conversation_id,
                            content=f"📋 **RESUMO DA CONVERSA (IA)**\n\n{summary}\n\n⚠️ *Transferido automaticamente: limite de mensagens atingido*",
                            private=True
                        )
                    except Exception as e:
                        logger.warning(f"[{slug}] Erro ao gerar resumo: {e}")

                # Fazer a transferência efetiva
                if ai_config.transfer_team_id:
                    try:
                        await chatwoot.assign_conversation_to_team(
                            conversation_id=conversation_id,
                            team_id=ai_config.transfer_team_id
                        )
                        team_members = await chatwoot.get_team_members(ai_config.transfer_team_id)
                        if team_members:
                            agent_index = conversation_id % len(team_members)
                            selected_agent = team_members[agent_index]
                            agent_id = selected_agent.get("id") or selected_agent.get("user_id")
                            if agent_id:
                                await chatwoot.assign_conversation_to_agent(
                                    conversation_id=conversation_id,
                                    assignee_id=agent_id
                                )
                                logger.info(f"[{slug}] Transferido para: {selected_agent.get('name', agent_id)}")
                    except Exception as e:
                        logger.error(f"[{slug}] Erro ao transferir: {e}")
                return

            # Buscar base de conhecimento (arquivos)
            result = await db.execute(
                select(AIKnowledgeFile).where(AIKnowledgeFile.client_slug == slug)
            )
            files = result.scalars().all()
            knowledge_base = "\n\n".join([f.content for f in files if f.content])

            # Buscar schema do cliente
            schema = None
            if client.product_schema_id:
                result = await db.execute(
                    select(ProductSchema).where(ProductSchema.id == client.product_schema_id)
                )
                schema_obj = result.scalar_one_or_none()
                if schema_obj:
                    schema = {"fields": schema_obj.fields or []}

            # Buscar produtos disponiveis
            result = await db.execute(
                select(Product).where(Product.client_slug == slug, Product.is_available == True)
            )
            products = result.scalars().all()

            products_list = []
            if products:
                minio = MinioService(
                    endpoint=settings.minio_endpoint,
                    access_key=settings.minio_access_key,
                    secret_key=settings.minio_secret_key,
                    secure=settings.minio_secure
                )

                for p in products:
                    product_dict = p.to_dict()
                    product_dict["embedding"] = p.embedding
                    if p.main_image:
                        try:
                            product_dict["main_image_url"] = minio.get_presigned_url(p.main_image)
                        except Exception as e:
                            logger.warning(f"[{slug}] Erro ao gerar URL da imagem: {e}")
                    products_list.append(product_dict)

            # === USAR LANGGRAPH AGENT ===
            logger.info(f"[{slug}] Msg: \"{truncate(message)}\" | Produtos: {len(products_list)}")

            # Tools habilitadas (default: todas)
            enabled_tools = ai_config.enabled_tools or ["buscar_produtos", "calcular_financiamento", "enviar_imagem", "agendar_visita", "transferir_atendimento"]

            # Preparar system prompt com instrucoes CRITICAS sobre as tools
            base_prompt = ai_config.system_prompt or "Voce e um assistente de vendas prestativo."

            # Instrucoes obrigatorias para forcar uso de tools
            tools_instruction = """

=== INSTRUCOES CRITICAS - LEIA COM ATENCAO ===

REGRA #1 - NOME DO CLIENTE:
- NUNCA use nomes como "Joao", "Maria", "Carlos" ou qualquer outro nome
- Se o cliente NAO disse o nome dele na conversa, NAO invente
- Use APENAS: "voce", "cliente" ou nao use nenhum nome
- Exemplo ERRADO: "Ate amanha, Joao!"
- Exemplo CORRETO: "Ate amanha! Sera um prazer te receber."

Voce e um agente de vendas com acesso a ferramentas (tools). Voce DEVE usar essas ferramentas.

REGRA ABSOLUTA: NUNCA invente informacoes sobre produtos, precos ou estoque.
Se o cliente perguntar QUALQUER coisa sobre produtos, veiculos, carros, precos, estoque ou disponibilidade:
-> Voce DEVE usar a ferramenta buscar_produtos PRIMEIRO
-> So responda DEPOIS de receber os dados da ferramenta
-> Use APENAS os dados retornados pela ferramenta

FLUXO OBRIGATORIO:
1. Cliente menciona produtos/carros/veiculos/estoque/precos -> USE buscar_produtos
2. Cliente pergunta financiamento/parcelas/entrada -> USE calcular_financiamento
3. Cliente pede foto/imagem -> USE enviar_imagem
4. Cliente quer agendar/visitar -> USE agendar_visita
5. Cliente CONFIRMA que vai visitar a loja (ex: "vou amanha", "as 12h", "fechado") -> USE transferir_atendimento
6. Cliente diz que quer FECHAR NEGOCIO ou COMPRAR -> USE transferir_atendimento
7. Cliente pede para falar com HUMANO/ATENDENTE -> USE transferir_atendimento

IMPORTANTE SOBRE TRANSFERENCIA:
- So transfira APOS ter mostrado pelo menos um produto com preco ao cliente
- Quando for transferir, SEMPRE inclua a palavra "consultor" na sua resposta
- Exemplos de frases para transferir:
  * "Vou transferir para um consultor finalizar o atendimento"
  * "Um consultor vai entrar em contato para dar continuidade"
  * "Estou encaminhando para um consultor especializado"
- A transferencia acontece automaticamente quando voce menciona "consultor" ou "especialista humano"

PROIBIDO:
- Inventar nomes de produtos
- Inventar precos
- Inventar nome do cliente (NUNCA use "Joao", "Maria", etc - veja REGRA #1)
- Dizer "vou verificar" sem usar a ferramenta
- Responder sobre produtos sem ter usado buscar_produtos
- Transferir antes de mostrar produtos ao cliente

Se voce responder sobre produtos SEM usar buscar_produtos, voce FALHOU na sua tarefa."""

            system_prompt = base_prompt + tools_instruction

            if knowledge_base:
                system_prompt += f"\n\n=== BASE DE CONHECIMENTO ===\n{knowledge_base}"

            # Log para debug
            logger.info(f"[{slug}] Tools habilitadas: {enabled_tools}")

            # Keywords configuraveis para forcar uso de tools (configuravel por tipo de negocio)
            product_keywords = ai_config.product_keywords or [
                "produto", "produtos", "estoque", "disponivel", "disponiveis",
                "tem", "temos", "quais", "preco", "precos", "quanto", "valor",
                "valores", "opcao", "opcoes", "ver", "mostrar", "conhecer", "saber"
            ]

            # Se tem imagem, NAO forcar busca automatica - deixar IA entender contexto
            skip_force_tools = has_image
            if skip_force_tools:
                logger.info(f"[{slug}] Imagem detectada - nao forcar busca automatica")

            # Modo de deteccao de intencao (keywords, auto, always)
            intent_mode = getattr(ai_config, 'intent_detection_mode', None) or 'keywords'

            # Keywords de transferencia configuraveis por cliente
            response_transfer_keywords = ai_config.transfer_keywords or ["consultor", "especialista humano", "transferindo"]

            result = await run_sales_agent(
                message=message,
                messages_history=messages[:-1],
                system_prompt=system_prompt,
                products=products_list,
                api_key=ai_config.api_key,
                model=ai_config.model,
                conversation_id=conversation_id,
                client_slug=slug,
                chatwoot_service=chatwoot,
                schema=schema,
                enabled_tools=enabled_tools,
                product_keywords=product_keywords,
                skip_force_tools=skip_force_tools,
                intent_detection_mode=intent_mode,
                transfer_keywords=response_transfer_keywords
            )

            if not result.get("success") or not result.get("response"):
                logger.error(f"[{slug}] Agente falhou: {result.get('error', 'sem resposta')}")
                return

            ai_response = result["response"]
            tools_used = result.get('tools_used', [])
            logger.info(f"[{slug}] Tools usadas: {tools_used}")

            # === REGISTRAR METRICAS DE ANALYTICS ===
            try:
                # Estimar tokens (aproximacao baseada em caracteres)
                tokens_input = estimate_tokens(message + system_prompt)
                tokens_output = estimate_tokens(ai_response)

                # Extrair IDs de produtos mostrados
                products_shown = []
                if "buscar_produtos" in tools_used or "ver_detalhes_produto" in tools_used:
                    products_shown = [p.id for p in products[:5] if hasattr(p, 'id')]

                # Extrair dados do contato
                sender = payload.get("sender", {})
                contact_phone = sender.get("phone_number")
                contact_name = sender.get("name")

                # Determinar outcome
                outcome = None
                if result.get("transfer_requested"):
                    outcome = "transferred"

                await AnalyticsService.record_conversation_metrics(
                    db=db,
                    client_slug=slug,
                    conversation_id=conversation_id,
                    tokens_input=tokens_input,
                    tokens_output=tokens_output,
                    tools_used=tools_used,
                    products_shown=products_shown,
                    channel="whatsapp",  # TODO: detectar canal do Chatwoot
                    contact_phone=contact_phone,
                    contact_name=contact_name,
                    transfer_requested=result.get("transfer_requested", False),
                    outcome=outcome
                )

                # Incrementar contador de mensagens
                await AnalyticsService.increment_message_count(
                    db=db,
                    client_slug=slug,
                    conversation_id=conversation_id,
                    is_ai_message=False  # Mensagem do usuario
                )
                await AnalyticsService.increment_message_count(
                    db=db,
                    client_slug=slug,
                    conversation_id=conversation_id,
                    is_ai_message=True  # Resposta da IA
                )

                logger.debug(f"[{slug}] Analytics registrado: {tokens_input}+{tokens_output} tokens")
            except Exception as analytics_error:
                logger.warning(f"[{slug}] Erro ao registrar analytics: {analytics_error}")

            # Adicionar resposta ao historico
            messages.append({"role": "assistant", "content": ai_response})
            ai_conv.messages = messages
            flag_modified(ai_conv, 'messages')
            await db.commit()

            # Dividir mensagem se necessario
            max_length = ai_config.split_message_at or 1000
            if max_length > 4000:
                max_length = 4000

            split_mode = getattr(ai_config, 'split_mode', None) or 'smart'
            parts = AIService.split_message(
                ai_response,
                max_length=max_length,
                split_by_paragraph=ai_config.split_by_paragraph if ai_config.split_by_paragraph is not None else True,
                split_mode=split_mode
            )

            # Enviar resposta(s) para o Chatwoot
            for part in parts:
                await chatwoot.send_message(
                    conversation_id=conversation_id,
                    content=part
                )

            if len(parts) > 1:
                logger.info(f"[{slug}] >> Enviado ({len(parts)} partes): \"{truncate(ai_response)}\"")
            else:
                logger.info(f"[{slug}] >> Enviado: \"{truncate(ai_response)}\"")

            # Enviar imagens pendentes (da tool enviar_imagem)
            # Nota: Enviamos SEM legenda pois a IA ja menciona a foto na resposta de texto
            pending_images = result.get("pending_images", [])
            if pending_images:
                logger.info(f"[{slug}] Enviando {len(pending_images)} imagem(ns) pendente(s)")
                for img in pending_images:
                    try:
                        await chatwoot.send_message_with_image(
                            conversation_id=conversation_id,
                            content="",  # Sem legenda para evitar duplicacao
                            image_url=img.get("url", "")
                        )
                        logger.info(f"[{slug}] >> Imagem enviada: {img.get('product_name', 'produto')}")
                    except Exception as img_error:
                        logger.error(f"[{slug}] Erro ao enviar imagem: {img_error}")

            # Processar transferencia para humano se solicitada
            transfer_requested = result.get("transfer_requested", False)
            if transfer_requested:
                logger.info(f"[{slug}] Transferencia solicitada - transferindo para equipe/humano")
                try:
                    # Adicionar label para indicar que precisa de atencao humana
                    await chatwoot.add_label(conversation_id, "atendimento_humano")

                    # Se tem equipe configurada, atribuir a ela
                    if ai_config.transfer_team_id:
                        await chatwoot.assign_conversation_to_team(
                            conversation_id=conversation_id,
                            team_id=ai_config.transfer_team_id
                        )
                        logger.info(f"[{slug}] Atribuido a equipe {ai_config.transfer_team_id}")

                        # Round-robin para um agente da equipe
                        team_members = await chatwoot.get_team_members(ai_config.transfer_team_id)
                        if team_members:
                            agent_index = conversation_id % len(team_members)
                            selected_agent = team_members[agent_index]
                            agent_id = selected_agent.get("id") or selected_agent.get("user_id")

                            if agent_id:
                                await chatwoot.assign_conversation_to_agent(
                                    conversation_id=conversation_id,
                                    assignee_id=agent_id
                                )
                                logger.info(f"[{slug}] Atribuido ao agente: {selected_agent.get('name', agent_id)}")
                        else:
                            logger.warning(f"[{slug}] Equipe {ai_config.transfer_team_id} sem membros")
                    else:
                        # Sem equipe configurada - apenas remove atribuicao do bot
                        await chatwoot.unassign_conversation(conversation_id)
                        logger.info(f"[{slug}] Conversa desatribuida (sem equipe configurada)")

                    logger.info(f"[{slug}] >> Conversa transferida para atendimento humano")
                except Exception as transfer_error:
                    logger.error(f"[{slug}] Erro ao transferir: {transfer_error}")

        except Exception as e:
            logger.error(f"[{slug}] Erro: {e}", exc_info=True)


@router.post("/{slug}")
async def receive_webhook(
    slug: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Recebe webhook do Chatwoot"""
    try:
        payload = await request.json()
        background_tasks.add_task(process_webhook, slug, payload)
        return {"status": "received"}
    except Exception as e:
        logger.error(f"[{slug}] Erro ao receber webhook: {e}")
        return {"status": "error", "message": str(e)}
