"""
Sales Agent Service usando LangGraph
Agente de IA para vendas com tools obrigatorias e thread-safety
"""
from typing import List, Dict, Optional, Any, Literal, Annotated, Sequence
from dataclasses import dataclass, field
from contextvars import ContextVar
import logging
import asyncio
import operator

# Imports de LangGraph/LangChain com tratamento de erro
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
except ImportError as e:
    raise ImportError(
        "langgraph nao esta instalado. Execute: pip install langgraph"
    ) from e

try:
    from langchain_openai import ChatOpenAI
    from langchain_core.tools import tool
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage, ToolMessage
except ImportError as e:
    raise ImportError(
        "langchain nao esta instalado. Execute: pip install langchain langchain-openai langchain-core"
    ) from e

from backend.services.rag_service import RAGService

logger = logging.getLogger(__name__)


# ============ CONTEXTO THREAD-SAFE ============
# Usar ContextVar ao inves de variavel global para thread-safety
_agent_context: ContextVar[Optional['AgentContext']] = ContextVar('agent_context', default=None)


@dataclass
class AgentContext:
    """Contexto compartilhado entre as tools do agente"""
    products: List[Dict]
    api_key: str
    conversation_id: int
    client_slug: str
    chatwoot_service: Any = None
    found_products: List[Dict] = field(default_factory=list)
    schema: Optional[Dict] = None
    product_keywords: List[str] = field(default_factory=lambda: [
        "produto", "produtos", "estoque", "disponivel", "disponiveis",
        "tem", "temos", "quais", "preco", "precos", "quanto", "valor",
        "valores", "opcao", "opcoes", "ver", "mostrar", "conhecer", "saber"
    ])
    # Imagens pendentes para enviar (preenchido pela tool enviar_imagem)
    pending_images: List[Dict] = field(default_factory=list)
    # Imagens ja enviadas nesta conversa (evitar duplicatas)
    sent_images: List[str] = field(default_factory=list)
    # Modo de deteccao de intencao: "keywords", "auto", "always"
    intent_detection_mode: str = "keywords"
    # Flag para solicitar transferencia para humano
    transfer_requested: bool = False
    # Keywords que ativam transferencia (configuravel por cliente)
    transfer_keywords: List[str] = field(default_factory=lambda: [
        "consultor", "especialista humano", "transferindo", "encaminhando para"
    ])


def set_context(ctx: AgentContext):
    """Define contexto de forma thread-safe"""
    _agent_context.set(ctx)


def get_context() -> Optional[AgentContext]:
    """Obtem contexto de forma thread-safe"""
    return _agent_context.get()


# ============ TOOLS ============

@tool
def buscar_produtos(query: str) -> str:
    """Busca produtos/veiculos na base de dados.
    OBRIGATORIO usar quando cliente perguntar sobre produtos, precos, disponibilidade, estoque, carros ou veiculos.

    Args:
        query: Termo de busca (ex: 'civic preto', 'carro ate 50 mil', 'estoque', 'carros disponiveis')

    Returns:
        Lista de produtos encontrados com detalhes completos incluindo precos e caracteristicas
    """
    ctx = get_context()
    if not ctx or not ctx.products:
        return "Nenhum produto disponivel na base no momento."

    logger.info(f"[TOOL] buscar_produtos: query='{query}' | Total na base={len(ctx.products)}")

    # Busca por keywords
    found = RAGService.keyword_search(query, ctx.products)[:5]

    # Fallback: retornar todos se nao encontrou com a busca
    if not found:
        logger.info(f"[TOOL] Busca sem resultado, retornando primeiros {min(5, len(ctx.products))} produtos")
        found = ctx.products[:5]

    if found:
        ctx.found_products = found
        result = RAGService.build_context_from_products(
            found, include_images=True, schema=ctx.schema
        )
        logger.info(f"[TOOL] buscar_produtos retornando {len(found)} produtos")
        return result

    return "Nenhum produto encontrado com esses criterios."


@tool
def calcular_financiamento(valor: float, entrada: float = 0, parcelas: int = 48) -> str:
    """Calcula simulacao de financiamento de veiculo.
    Use quando cliente perguntar sobre parcelas, financiamento, como pagar ou formas de pagamento.

    Args:
        valor: Valor total do veiculo em reais
        entrada: Valor da entrada em reais (padrao 0)
        parcelas: Numero de parcelas desejadas (padrao 48)

    Returns:
        Simulacao completa com valores de parcela, total e juros
    """
    logger.info(f"[TOOL] calcular_financiamento: valor={valor}, entrada={entrada}, parcelas={parcelas}")

    taxa_mensal = 1.99 / 100
    valor_financiado = valor - entrada

    if valor_financiado <= 0:
        return "Valor da entrada deve ser menor que o valor total do veiculo."

    # Calculo Price
    parcela = valor_financiado * (taxa_mensal * (1 + taxa_mensal) ** parcelas) / ((1 + taxa_mensal) ** parcelas - 1)
    total = parcela * parcelas
    juros_total = total - valor_financiado

    def fmt(v):
        return f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return f"""=== SIMULACAO DE FINANCIAMENTO ===
Valor do veiculo: {fmt(valor)}
Entrada: {fmt(entrada)}
Valor financiado: {fmt(valor_financiado)}
Parcelas: {parcelas}x de {fmt(parcela)}
Taxa mensal: 1.99%
Total a pagar: {fmt(total)}
Total de juros: {fmt(juros_total)}

* Valores aproximados, sujeitos a analise de credito."""


@tool
def ver_detalhes_produto(produto_nome: str) -> str:
    """Mostra detalhes completos de um produto especifico.
    Use quando cliente quiser saber mais sobre um produto especifico ja mencionado.

    Args:
        produto_nome: Nome ou parte do nome do produto

    Returns:
        Detalhes completos do produto com todas as especificacoes
    """
    ctx = get_context()
    if not ctx:
        return "Erro: contexto nao disponivel."

    # Se nao tem produtos encontrados, buscar na base completa
    search_list = ctx.found_products if ctx.found_products else ctx.products

    if not search_list:
        return "Nenhum produto disponivel. Use buscar_produtos primeiro."

    logger.info(f"[TOOL] ver_detalhes_produto: nome='{produto_nome}'")

    # Encontrar produto
    produto = None
    for p in search_list:
        if produto_nome.lower() in p.get("name", "").lower():
            produto = p
            break

    # Fallback: primeiro produto
    if not produto and search_list:
        produto = search_list[0]

    if produto:
        return RAGService.build_context_from_products(
            [produto], include_images=True, schema=ctx.schema
        )

    return f"Produto '{produto_nome}' nao encontrado."


@tool
def agendar_visita(data: str, horario: str = "", nome_cliente: str = "", telefone: str = "") -> str:
    """Agenda visita do cliente a loja para ver os veiculos.
    Use quando cliente quiser agendar, marcar horario, visitar a loja ou conhecer os carros pessoalmente.

    Args:
        data: Data desejada (ex: 'sabado', 'amanha', '15/02')
        horario: Horario preferido (ex: 'manha', '14h', 'tarde')
        nome_cliente: Nome do cliente para contato
        telefone: Telefone para confirmacao

    Returns:
        Confirmacao do agendamento solicitado
    """
    ctx = get_context()
    logger.info(f"[TOOL] agendar_visita: data={data}, horario={horario}")

    return f"""=== AGENDAMENTO REGISTRADO ===
Data solicitada: {data}
Horario: {horario or 'A confirmar'}
Cliente: {nome_cliente or 'Nao informado'}
Telefone: {telefone or 'Nao informado'}
Conversa: #{ctx.conversation_id if ctx else 'N/A'}

Um consultor entrara em contato para confirmar o agendamento."""


@tool
def enviar_imagem(produto_nome: str, mensagem: str = "") -> str:
    """Envia a foto/imagem de um produto para o cliente.
    Use APENAS quando o cliente PEDIR EXPLICITAMENTE para ver foto, imagem ou visualizar um produto.
    NAO use esta tool se a imagem do produto JA FOI ENVIADA antes na conversa.
    A imagem sera enviada automaticamente apos sua resposta.

    Args:
        produto_nome: Nome do produto para enviar a foto
        mensagem: Mensagem opcional para acompanhar a imagem

    Returns:
        Confirmacao de que a imagem sera enviada
    """
    ctx = get_context()
    if not ctx:
        return "Erro: contexto nao disponivel."

    search_list = ctx.found_products if ctx.found_products else ctx.products

    if not search_list:
        return "Nenhum produto disponivel. Use buscar_produtos primeiro."

    logger.info(f"[TOOL] enviar_imagem: nome='{produto_nome}'")

    # Encontrar produto
    produto = None
    for p in search_list:
        if produto_nome.lower() in p.get("name", "").lower():
            produto = p
            break

    if not produto and search_list:
        produto = search_list[0]

    if produto:
        product_name = produto.get('name', 'produto')
        image_url = produto.get("main_image_url")

        # Verificar se imagem ja foi enviada nesta conversa
        if product_name.lower() in [s.lower() for s in ctx.sent_images]:
            logger.info(f"[TOOL] Imagem ja enviada anteriormente: {product_name}")
            return f"A foto do {product_name} JA FOI ENVIADA anteriormente nesta conversa. NAO envie novamente."

        if image_url:
            # Armazenar imagem pendente para ser enviada pelo webhook handler
            ctx.pending_images.append({
                "url": image_url,
                "caption": mensagem or f"Foto do {product_name}",
                "product_name": product_name
            })
            # Marcar como enviada
            ctx.sent_images.append(product_name)
            logger.info(f"[TOOL] Imagem pendente adicionada: {product_name}")
            return f"[FOTO SERA ENVIADA] A foto do {product_name} sera enviada ao cliente. NAO inclua a URL na sua resposta - a imagem sera enviada automaticamente."
        else:
            return f"O produto {product_name} nao possui foto cadastrada."

    return f"Produto '{produto_nome}' nao encontrado."


@tool
def transferir_atendimento(motivo: str = "") -> str:
    """Transfere o atendimento para um consultor humano.
    Use quando:
    - Cliente quer FECHAR NEGOCIO ou comprar
    - Cliente pede para falar com humano/atendente
    - Cliente quer negociar preco ou condicoes especiais
    - Assunto fora do seu conhecimento
    - Cliente vai visitar a loja presencialmente

    Args:
        motivo: Motivo da transferencia para o consultor

    Returns:
        Confirmacao da transferencia
    """
    ctx = get_context()
    if not ctx:
        return "Erro: contexto nao disponivel."

    logger.info(f"[TOOL] transferir_atendimento: motivo='{motivo}'")

    # Marcar flag para transferencia
    ctx.transfer_requested = True

    return f"""[TRANSFERENCIA SOLICITADA]
Motivo: {motivo or 'Cliente pronto para fechar negocio'}
Conversa: #{ctx.conversation_id}

Um consultor humano assumira o atendimento em breve.
Informe ao cliente que ele sera atendido por um especialista."""


# Lista de tools disponiveis
TOOLS = [
    buscar_produtos,
    calcular_financiamento,
    ver_detalhes_produto,
    agendar_visita,
    enviar_imagem,
    transferir_atendimento
]

# Map de tools por nome
TOOLS_BY_NAME = {t.name: t for t in TOOLS}


# ============ STATE DO AGENTE ============

from typing import TypedDict

class AgentState(TypedDict):
    """Estado do agente LangGraph"""
    messages: Annotated[Sequence[BaseMessage], operator.add]
    tools_used: List[str]


# ============ AGENTE LANGGRAPH COM TOOL_CHOICE ============

class SalesAgentLangGraph:
    """Agente de vendas usando LangGraph com tool_choice='required' para forcar uso de tools"""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self.checkpointer = MemorySaver()

    def _should_use_tools(self, message: str, keywords: List[str]) -> bool:
        """Determina se a mensagem requer uso de tools baseado em keywords configuraveis"""
        lower_msg = message.lower()
        return any(kw.lower() in lower_msg for kw in keywords)

    async def _detect_intent_auto(self, message: str, history: List[BaseMessage]) -> bool:
        """
        Usa o LLM para detectar automaticamente se a mensagem requer busca de produtos.
        Retorna True se deve forcar uso de tools.
        """
        try:
            llm = ChatOpenAI(
                api_key=self.api_key,
                model="gpt-4o-mini",  # Modelo rapido para classificacao
                temperature=0
            )

            # Pegar ultimas mensagens para contexto
            recent_context = ""
            for msg in history[-4:]:
                if isinstance(msg, HumanMessage):
                    recent_context += f"Cliente: {msg.content[:100]}\n"
                elif isinstance(msg, AIMessage):
                    recent_context += f"Assistente: {msg.content[:100]}\n"

            classification_prompt = f"""Analise a mensagem do cliente e o contexto da conversa.

Contexto recente:
{recent_context}

Mensagem atual: "{message}"

Responda "SIM" APENAS se o cliente esta PEDINDO para:
- Ver/buscar novos produtos ou veiculos
- Saber precos ou disponibilidade de itens NAO mencionados
- Comparar opcoes ou ver alternativas novas
- Conhecer caracteristicas de produtos ainda nao apresentados

Responda "NAO" se o cliente esta:
- Confirmando algo (ex: "vou querer", "fechado", "ok", "blz")
- Falando sobre pagamento/forma de pagar
- Dizendo que vai visitar a loja
- Dando seu nome ou dados pessoais
- Agradecendo ou se despedindo
- Respondendo uma pergunta sua
- Ja decidiu e quer fechar negocio

Lembre-se: Se o produto JA FOI mostrado na conversa, NAO precisa buscar de novo.

Resposta (apenas SIM ou NAO):"""

            response = await llm.ainvoke([HumanMessage(content=classification_prompt)])
            result = response.content.strip().upper()

            should_search = "SIM" in result
            logger.info(f"[Intent] Auto-detect: '{message[:50]}...' -> {result} -> force_tools={should_search}")

            return should_search

        except Exception as e:
            logger.warning(f"[Intent] Erro na deteccao automatica: {e}. Usando fallback keywords.")
            return False

    async def _detect_transfer_scenario(self, message: str, history: List[BaseMessage]) -> bool:
        """
        Analise inteligente do fluxo de vendas para determinar o momento ideal de transferencia.
        Considera o estagio do funil de vendas e sinais de prontidao do cliente.
        """
        try:
            llm = ChatOpenAI(
                api_key=self.api_key,
                model="gpt-4o-mini",
                temperature=0
            )

            # Pegar mais contexto para analise completa do fluxo
            conversation_flow = ""
            for i, msg in enumerate(history[-10:]):
                if isinstance(msg, HumanMessage):
                    conversation_flow += f"[{i+1}] Cliente: {msg.content[:200]}\n"
                elif isinstance(msg, AIMessage):
                    conversation_flow += f"[{i+1}] Vendedor: {msg.content[:200]}\n"
                elif isinstance(msg, ToolMessage):
                    # Indicar que houve busca de produtos ou outra acao
                    conversation_flow += f"[{i+1}] [Sistema buscou informacoes]\n"

            transfer_prompt = f"""Voce e um especialista em analise de funil de vendas.
Analise o fluxo COMPLETO da conversa e determine se chegou o momento de transferir para um consultor humano.

=== FLUXO DA CONVERSA ===
{conversation_flow}

=== MENSAGEM ATUAL DO CLIENTE ===
"{message}"

=== ESTAGIOS DO FUNIL DE VENDAS ===
1. DESCOBERTA: Cliente esta apenas conhecendo, fazendo perguntas gerais
2. INTERESSE: Cliente perguntou sobre produto especifico, viu precos
3. CONSIDERACAO: Cliente compara opcoes, pergunta sobre pagamento/financiamento
4. DECISAO: Cliente demonstra intencao clara de compra ou visita
5. ACAO: Cliente confirma que vai comprar/visitar/fechar negocio

=== PRE-REQUISITO OBRIGATORIO PARA TRANSFERIR ===
O vendedor JA DEVE TER mostrado pelo menos UM produto com preco na conversa.
Se o vendedor ainda NAO mostrou nenhum produto/preco, responda NAO.

=== QUANDO TRANSFERIR (responda TRANSFERIR) ===
APENAS se o pre-requisito acima foi cumprido E:
- Cliente CONFIRMOU data/horario para visitar (ex: "amanha as 12", "vou sabado")
- Cliente disse "fechado", "combinado", "vou querer esse" apos ver produto
- Cliente pediu para falar com pessoa/humano/gerente
- Cliente respondeu pergunta sobre horario com confirmacao definitiva
- Cliente disse que vai na loja E confirmou quando

=== QUANDO NAO TRANSFERIR (responda NAO) ===
- Vendedor AINDA NAO mostrou nenhum produto com preco (SEMPRE NAO neste caso!)
- Cliente apenas disse que quer comprar mas NAO viu produtos ainda
- Cliente esta fazendo perguntas sobre produtos
- Cliente apenas demonstrou interesse mas nao confirmou nada
- Cliente esta comparando opcoes ou pensando
- Cliente fez saudacao ou pergunta generica
- Vendedor fez pergunta e cliente ainda nao respondeu
- Cliente disse "vou pensar", "deixa eu ver", "talvez"
- Cliente mencionou forma de pagamento mas NAO confirmou compra/visita

=== ANALISE ===
1. Em qual estagio do funil o cliente esta?
2. A mensagem atual indica CONFIRMACAO definitiva ou apenas interesse?
3. O cliente ja viu produto/preco E esta confirmando proximos passos?

Responda APENAS uma palavra:
- "TRANSFERIR" se o cliente confirmou decisao e esta pronto para atendimento humano
- "NAO" se ainda esta em fase de descoberta/interesse/consideracao

Resposta:"""

            response = await llm.ainvoke([HumanMessage(content=transfer_prompt)])
            result = response.content.strip().upper()

            should_transfer = "TRANSFERIR" in result
            logger.info(f"[Transfer] Analise funil: '{message[:40]}...' -> {result}")

            return should_transfer

        except Exception as e:
            logger.warning(f"[Transfer] Erro na analise: {e}")
            return False

    async def process_message(
        self,
        message: str,
        messages_history: List[Dict],
        system_prompt: str,
        context: AgentContext,
        enabled_tools: Optional[List[str]] = None,
        skip_force_tools: bool = False
    ) -> Dict[str, Any]:
        """Processa mensagem usando LangGraph com tool_choice='required'"""
        try:
            # Definir contexto thread-safe
            set_context(context)

            # Filtrar tools habilitadas
            if enabled_tools:
                active_tools = [t for t in TOOLS if t.name in enabled_tools]
            else:
                active_tools = TOOLS

            tool_names = [t.name for t in active_tools]
            logger.info(f"[LangGraph] Tools ativas: {tool_names}")

            # Criar LLM
            llm = ChatOpenAI(
                api_key=self.api_key,
                model=self.model,
                temperature=0.3
            )

            # Preparar mensagens
            all_messages = [SystemMessage(content=system_prompt)]

            for msg in messages_history[-10:]:
                if msg.get("role") == "user":
                    all_messages.append(HumanMessage(content=msg["content"]))
                else:
                    all_messages.append(AIMessage(content=msg["content"]))

            all_messages.append(HumanMessage(content=message))

            logger.info(f"[LangGraph] Processando: '{message[:50]}...'")

            tools_used = []

            # Verificar se deve forcar uso de tools baseado no modo de deteccao
            # NAO forcar se skip_force_tools=True (ex: quando tem imagem, deixar IA entender contexto)
            should_force_tools = False

            if not skip_force_tools:
                intent_mode = context.intent_detection_mode or "keywords"

                if intent_mode == "always":
                    # Sempre forca busca de produtos
                    should_force_tools = True
                    logger.info(f"[LangGraph] Modo 'always' - forcando tools")

                elif intent_mode == "auto":
                    # Usa IA para detectar intencao automaticamente
                    should_force_tools = await self._detect_intent_auto(message, all_messages)
                    logger.info(f"[LangGraph] Modo 'auto' - IA detectou: force_tools={should_force_tools}")

                else:  # "keywords" (padrao)
                    should_force_tools = self._should_use_tools(message, context.product_keywords)
                    logger.info(f"[LangGraph] Modo 'keywords' - detectado: force_tools={should_force_tools}")
            else:
                logger.info(f"[LangGraph] skip_force_tools=True - nao forcando tools")

            if should_force_tools and active_tools:
                # PASSO 1: Chamar modelo com tool_choice='required' para forcar uso de tool
                logger.info("[LangGraph] Forcando uso de tool (tool_choice='required')")

                llm_with_forced_tools = llm.bind_tools(active_tools, tool_choice="required")

                first_response = await llm_with_forced_tools.ainvoke(all_messages)

                # Processar tool calls
                if first_response.tool_calls:
                    all_messages.append(first_response)

                    for tool_call in first_response.tool_calls:
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", "")

                        logger.info(f"[LangGraph] Executando tool: {tool_name}({tool_args})")
                        tools_used.append(tool_name)

                        # Executar tool
                        if tool_name in TOOLS_BY_NAME:
                            try:
                                tool_result = TOOLS_BY_NAME[tool_name].invoke(tool_args)
                                logger.info(f"[LangGraph] Tool {tool_name} retornou {len(str(tool_result))} chars")
                            except Exception as e:
                                logger.error(f"[LangGraph] Erro na tool {tool_name}: {e}")
                                tool_result = f"Erro ao executar {tool_name}: {str(e)}"
                        else:
                            tool_result = f"Tool {tool_name} nao encontrada"

                        # Adicionar resultado da tool
                        all_messages.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_id
                        ))

                    # PASSO 2: Chamar modelo novamente para gerar resposta final (sem forcar tools)
                    logger.info("[LangGraph] Gerando resposta final com dados das tools")
                    llm_for_response = llm.bind_tools(active_tools)  # tools disponiveis mas nao obrigatorias
                    final_response = await llm_for_response.ainvoke(all_messages)

                    # Loop adicional se modelo quiser usar mais tools
                    max_iterations = 3
                    iteration = 0

                    while final_response.tool_calls and iteration < max_iterations:
                        iteration += 1
                        all_messages.append(final_response)

                        for tool_call in final_response.tool_calls:
                            tool_name = tool_call.get("name", "")
                            tool_args = tool_call.get("args", {})
                            tool_id = tool_call.get("id", "")

                            logger.info(f"[LangGraph] Executando tool adicional: {tool_name}")
                            tools_used.append(tool_name)

                            if tool_name in TOOLS_BY_NAME:
                                try:
                                    tool_result = TOOLS_BY_NAME[tool_name].invoke(tool_args)
                                except Exception as e:
                                    tool_result = f"Erro: {str(e)}"
                            else:
                                tool_result = f"Tool {tool_name} nao encontrada"

                            all_messages.append(ToolMessage(
                                content=str(tool_result),
                                tool_call_id=tool_id
                            ))

                        final_response = await llm_for_response.ainvoke(all_messages)

                    response_text = final_response.content
                else:
                    # Modelo nao chamou tools mesmo com tool_choice='required' (raro)
                    logger.warning("[LangGraph] Modelo nao usou tools mesmo com tool_choice='required'")
                    response_text = first_response.content
            else:
                # Mensagem simples - nao forcar tools
                logger.info("[LangGraph] Mensagem simples - tools opcionais")
                llm_with_tools = llm.bind_tools(active_tools)

                response = await llm_with_tools.ainvoke(all_messages)

                # Se modelo escolheu usar tools, processar
                while response.tool_calls:
                    all_messages.append(response)

                    for tool_call in response.tool_calls:
                        tool_name = tool_call.get("name", "")
                        tool_args = tool_call.get("args", {})
                        tool_id = tool_call.get("id", "")

                        logger.info(f"[LangGraph] Executando tool: {tool_name}")
                        tools_used.append(tool_name)

                        if tool_name in TOOLS_BY_NAME:
                            try:
                                tool_result = TOOLS_BY_NAME[tool_name].invoke(tool_args)
                            except Exception as e:
                                tool_result = f"Erro: {str(e)}"
                        else:
                            tool_result = f"Tool {tool_name} nao encontrada"

                        all_messages.append(ToolMessage(
                            content=str(tool_result),
                            tool_call_id=tool_id
                        ))

                    response = await llm_with_tools.ainvoke(all_messages)

                response_text = response.content

            logger.info(f"[LangGraph] Tools usadas: {tools_used}")
            logger.info(f"[LangGraph] Resposta ({len(response_text)} chars): '{response_text[:80]}...'")
            logger.info(f"[LangGraph] Imagens pendentes: {len(context.pending_images)}")

            # Verificar se deveria transferir
            # Metodo 1: Detectar palavras-chave na resposta da IA (mais rapido e confiavel)
            # Usa keywords configuraveis por cliente
            response_lower = response_text.lower()
            keyword_transfer = any(kw.lower() in response_lower for kw in context.transfer_keywords)

            if keyword_transfer and not context.transfer_requested:
                logger.info(f"[LangGraph] Keyword de transferencia detectada na resposta")
                context.transfer_requested = True
                tools_used.append("transferir_atendimento")

            # Metodo 2: Analise de funil (fallback se nao detectou por keyword)
            if not context.transfer_requested and "transferir_atendimento" in (enabled_tools or []):
                should_transfer = await self._detect_transfer_scenario(message, all_messages)
                if should_transfer:
                    logger.info("[LangGraph] Detectado cenario de transferencia via analise de funil")
                    context.transfer_requested = True
                    tools_used.append("transferir_atendimento")

            logger.info(f"[LangGraph] Transferencia solicitada: {context.transfer_requested}")

            return {
                "response": response_text,
                "tools_used": list(set(tools_used)),
                "pending_images": context.pending_images,
                "transfer_requested": context.transfer_requested,
                "success": True
            }

        except Exception as e:
            logger.error(f"[LangGraph] Erro no agente: {e}", exc_info=True)
            return {
                "response": "",
                "tools_used": [],
                "pending_images": [],
                "success": False,
                "error": str(e)
            }


# ============ FUNCAO DE CONVENIENCIA (mantem compatibilidade) ============

async def run_sales_agent(
    message: str,
    messages_history: List[Dict],
    system_prompt: str,
    products: List[Dict],
    api_key: str,
    model: str,
    conversation_id: int,
    client_slug: str,
    chatwoot_service=None,
    schema: Optional[Dict] = None,
    enabled_tools: Optional[List[str]] = None,
    product_keywords: Optional[List[str]] = None,
    skip_force_tools: bool = False,
    intent_detection_mode: str = "keywords",
    transfer_keywords: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Funcao de conveniencia para executar o agente de vendas.
    Mantem a mesma assinatura para compatibilidade com webhook.py

    Args:
        product_keywords: Lista de palavras-chave que forcam uso de tools (configuravel por cliente)
        skip_force_tools: Se True, nao forca uso de tools mesmo com keywords (ex: quando tem imagem)
        intent_detection_mode: Modo de deteccao de intencao ("keywords", "auto", "always")
        transfer_keywords: Lista de palavras-chave na resposta da IA que ativam transferencia
    """
    # Keywords padrao se nao fornecidas
    default_product_keywords = [
        "produto", "produtos", "estoque", "disponivel", "disponiveis",
        "tem", "temos", "quais", "preco", "precos", "quanto", "valor",
        "valores", "opcao", "opcoes", "ver", "mostrar", "conhecer", "saber"
    ]

    # Keywords de transferencia padrao
    default_transfer_keywords = [
        "consultor", "especialista humano", "transferindo", "encaminhando para"
    ]

    # Criar contexto
    context = AgentContext(
        products=products,
        api_key=api_key,
        conversation_id=conversation_id,
        client_slug=client_slug,
        chatwoot_service=chatwoot_service,
        schema=schema,
        product_keywords=product_keywords or default_product_keywords,
        intent_detection_mode=intent_detection_mode,
        transfer_keywords=transfer_keywords or default_transfer_keywords
    )

    # Criar e executar agente
    agent = SalesAgentLangGraph(api_key=api_key, model=model)

    return await agent.process_message(
        message=message,
        messages_history=messages_history,
        system_prompt=system_prompt,
        context=context,
        enabled_tools=enabled_tools,
        skip_force_tools=skip_force_tools
    )
