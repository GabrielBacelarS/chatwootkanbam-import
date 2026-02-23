"""
Servico para simulacao de conversas completas com agentes IA
Simula um cliente real conversando em multiplos turnos
"""
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import google.generativeai as genai

from backend.services.sales_agent_service import run_sales_agent

logger = logging.getLogger(__name__)


class ConversationSimulatorService:
    """Simula conversas completas entre cliente virtual e agente IA"""

    CLIENT_PERSONA_PROMPT = """Voce e um CLIENTE interessado em comprar produtos de uma loja.
Voce esta conversando via WhatsApp com um vendedor.

CONTEXTO DA LOJA:
{business_context}

PRODUTOS DISPONIVEIS:
{products_summary}

SEU PERFIL DE CLIENTE:
{client_profile}

SEU OBJETIVO NESTA CONVERSA:
{conversation_goal}

REGRAS DE COMPORTAMENTO:
1. Responda de forma NATURAL como um cliente real de WhatsApp
2. Use linguagem informal mas educada
3. Faca perguntas de acompanhamento baseadas nas respostas do vendedor
4. Demonstre interesse genuino nos produtos
5. Reaja as informacoes recebidas (precos, caracteristicas, etc)
6. Se o vendedor pedir informacoes, forneca dados ficticios realistas
7. A conversa deve progredir naturalmente ate seu objetivo
8. Responda em 1-3 frases curtas (estilo WhatsApp)

HISTORICO DA CONVERSA ATE AGORA:
{conversation_history}

ULTIMA MENSAGEM DO VENDEDOR:
{last_agent_message}

Responda como o cliente responderia naturalmente:"""

    CLIENT_PROFILES = [
        {
            "name": "Cliente Direto",
            "description": "Sabe o que quer, vai direto ao ponto",
            "style": "Objetivo, faz perguntas especificas, quer informacoes rapidas"
        },
        {
            "name": "Cliente Indeciso",
            "description": "Precisa de ajuda para decidir",
            "style": "Faz muitas perguntas, compara opcoes, pede opiniao do vendedor"
        },
        {
            "name": "Cliente Detalhista",
            "description": "Quer saber todos os detalhes antes de comprar",
            "style": "Pergunta especificacoes tecnicas, historico, garantia, condicoes"
        },
        {
            "name": "Cliente Apressado",
            "description": "Tem pouco tempo, quer resolver rapido",
            "style": "Mensagens curtas, quer respostas diretas, pode agendar visita rapido"
        },
        {
            "name": "Cliente Negociador",
            "description": "Quer o melhor preco possivel",
            "style": "Pergunta sobre descontos, parcelas, entrada, tenta negociar"
        }
    ]

    CONVERSATION_GOALS = [
        "Encontrar um produto que atenda suas necessidades e pedir mais informacoes",
        "Comparar 2-3 produtos e escolher o melhor custo-beneficio",
        "Simular um financiamento e entender as condicoes de pagamento",
        "Agendar uma visita para ver os produtos pessoalmente",
        "Pedir fotos e mais detalhes de produtos especificos",
        "Entender a disponibilidade e fazer uma reserva",
        "Negociar preco e condicoes especiais"
    ]

    @staticmethod
    def _summarize_products(products: List[Dict], max_products: int = 10) -> str:
        """Resume produtos para o contexto"""
        if not products:
            return "Nenhum produto disponivel."

        lines = []
        for p in products[:max_products]:
            name = p.get("name", "Produto")
            price = p.get("price", 0)
            data = p.get("data", {}) or {}
            extras = [f"{k}: {v}" for k, v in list(data.items())[:3] if v]
            line = f"- {name} | R$ {price:,.0f}"
            if extras:
                line += f" | {', '.join(extras)}"
            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _format_history(messages: List[Dict]) -> str:
        """Formata historico de conversa"""
        if not messages:
            return "(Inicio da conversa)"

        lines = []
        for msg in messages:
            role = "CLIENTE" if msg["role"] == "user" else "VENDEDOR"
            lines.append(f"{role}: {msg['content']}")

        return "\n".join(lines)

    @staticmethod
    async def generate_client_response_openai(
        api_key: str,
        model: str,
        business_context: str,
        products: List[Dict],
        client_profile: Dict,
        conversation_goal: str,
        conversation_history: List[Dict],
        last_agent_message: str
    ) -> str:
        """Gera resposta do cliente simulado usando OpenAI"""
        client = AsyncOpenAI(api_key=api_key)

        prompt = ConversationSimulatorService.CLIENT_PERSONA_PROMPT.format(
            business_context=business_context or "Loja de produtos diversos",
            products_summary=ConversationSimulatorService._summarize_products(products),
            client_profile=f"{client_profile['name']}: {client_profile['style']}",
            conversation_goal=conversation_goal,
            conversation_history=ConversationSimulatorService._format_history(conversation_history),
            last_agent_message=last_agent_message
        )

        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Voce simula um cliente real conversando via WhatsApp."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.9,
            max_tokens=150
        )

        return response.choices[0].message.content.strip()

    @staticmethod
    async def generate_client_response_gemini(
        api_key: str,
        model: str,
        business_context: str,
        products: List[Dict],
        client_profile: Dict,
        conversation_goal: str,
        conversation_history: List[Dict],
        last_agent_message: str
    ) -> str:
        """Gera resposta do cliente simulado usando Gemini"""
        genai.configure(api_key=api_key)

        prompt = ConversationSimulatorService.CLIENT_PERSONA_PROMPT.format(
            business_context=business_context or "Loja de produtos diversos",
            products_summary=ConversationSimulatorService._summarize_products(products),
            client_profile=f"{client_profile['name']}: {client_profile['style']}",
            conversation_goal=conversation_goal,
            conversation_history=ConversationSimulatorService._format_history(conversation_history),
            last_agent_message=last_agent_message
        )

        def generate_sync():
            model_instance = genai.GenerativeModel(
                model_name=model,
                generation_config={"temperature": 0.9, "max_output_tokens": 150}
            )
            response = model_instance.generate_content(prompt)
            return response.text

        return await asyncio.get_event_loop().run_in_executor(None, generate_sync)

    @staticmethod
    async def generate_client_response(
        api_key: str,
        model: str,
        business_context: str,
        products: List[Dict],
        client_profile: Dict,
        conversation_goal: str,
        conversation_history: List[Dict],
        last_agent_message: str
    ) -> str:
        """Gera resposta do cliente simulado"""
        if "gemini" in model.lower():
            return await ConversationSimulatorService.generate_client_response_gemini(
                api_key, model, business_context, products,
                client_profile, conversation_goal, conversation_history, last_agent_message
            )
        else:
            return await ConversationSimulatorService.generate_client_response_openai(
                api_key, model, business_context, products,
                client_profile, conversation_goal, conversation_history, last_agent_message
            )

    @staticmethod
    async def run_conversation(
        api_key: str,
        model: str,
        system_prompt: str,
        products: List[Dict],
        enabled_tools: List[str],
        client_slug: str,
        num_turns: int = 5,
        client_profile: Dict = None,
        conversation_goal: str = None,
        initial_message: str = None,
        schema: Dict = None,
        product_keywords: List[str] = None
    ) -> Dict[str, Any]:
        """
        Executa uma conversa completa entre cliente simulado e agente.

        Args:
            api_key: Chave da API
            model: Modelo a usar
            system_prompt: Prompt do agente
            products: Lista de produtos
            enabled_tools: Ferramentas habilitadas
            client_slug: Slug do cliente
            num_turns: Numero de turnos da conversa
            client_profile: Perfil do cliente (opcional, escolhe aleatorio)
            conversation_goal: Objetivo da conversa (opcional)
            initial_message: Mensagem inicial (opcional)
            schema: Schema de produtos
            product_keywords: Keywords de produtos

        Returns:
            Dict com historico da conversa, tools usadas, avaliacao
        """
        import random

        # Escolher perfil e objetivo se nao fornecidos
        if client_profile is None:
            client_profile = random.choice(ConversationSimulatorService.CLIENT_PROFILES)

        if conversation_goal is None:
            conversation_goal = random.choice(ConversationSimulatorService.CONVERSATION_GOALS)

        # Gerar mensagem inicial se nao fornecida
        if initial_message is None:
            initial_messages = [
                "Oi, boa tarde! Vi que voces tem produtos disponiveis, queria saber mais",
                "Ola! Estou procurando algo especifico, podem me ajudar?",
                "Oi, tudo bem? Queria ver o que voces tem disponivel",
                "Boa tarde! Um amigo me indicou voces, estou interessado nos produtos",
                "Oi! Vi o anuncio e gostei, podem me mostrar as opcoes?",
            ]
            initial_message = random.choice(initial_messages)

        conversation_history = []
        all_tools_used = []
        turn_details = []

        # Primeira mensagem do cliente
        current_client_message = initial_message

        for turn in range(num_turns):
            logger.info(f"[ConvSim] Turno {turn + 1}/{num_turns}")

            # Adicionar mensagem do cliente ao historico
            conversation_history.append({
                "role": "user",
                "content": current_client_message
            })

            # Executar agente
            agent_result = await run_sales_agent(
                message=current_client_message,
                messages_history=conversation_history[:-1],  # Historico sem a mensagem atual
                system_prompt=system_prompt,
                products=products,
                api_key=api_key,
                model=model,
                conversation_id=0,
                client_slug=client_slug,
                chatwoot_service=None,
                schema=schema,
                enabled_tools=enabled_tools,
                product_keywords=product_keywords
            )

            agent_response = agent_result.get("response", "")
            tools_used = agent_result.get("tools_used", [])
            all_tools_used.extend(tools_used)

            # Adicionar resposta do agente ao historico
            conversation_history.append({
                "role": "assistant",
                "content": agent_response
            })

            turn_details.append({
                "turn": turn + 1,
                "client_message": current_client_message,
                "agent_response": agent_response,
                "tools_used": tools_used
            })

            # Se nao for o ultimo turno, gerar proxima mensagem do cliente
            if turn < num_turns - 1:
                try:
                    current_client_message = await ConversationSimulatorService.generate_client_response(
                        api_key=api_key,
                        model=model,
                        business_context=system_prompt[:500] if system_prompt else "",
                        products=products,
                        client_profile=client_profile,
                        conversation_goal=conversation_goal,
                        conversation_history=conversation_history,
                        last_agent_message=agent_response
                    )
                except Exception as e:
                    logger.error(f"[ConvSim] Erro ao gerar resposta do cliente: {e}")
                    current_client_message = "Entendi, pode me contar mais?"

        # Calcular metricas
        unique_tools = list(set(all_tools_used))

        # Avaliar conversa automaticamente
        evaluation = ConversationSimulatorService.evaluate_conversation(
            turn_details=turn_details,
            tools_used=unique_tools,
            conversation_goal=conversation_goal,
            enabled_tools=enabled_tools
        )

        return {
            "client_profile": client_profile["name"],
            "conversation_goal": conversation_goal,
            "num_turns": num_turns,
            "conversation_history": conversation_history,
            "turn_details": turn_details,
            "tools_used": unique_tools,
            "total_tool_calls": len(all_tools_used),
            "evaluation": evaluation
        }

    @staticmethod
    def evaluate_conversation(
        turn_details: List[Dict],
        tools_used: List[str],
        conversation_goal: str,
        enabled_tools: List[str] = None
    ) -> Dict[str, Any]:
        """
        Avalia a qualidade de uma conversa simulada.
        Retorna scores de 0-10 para diferentes criterios.
        """
        scores = {}
        issues = []

        # 1. TOOL USAGE (25%) - Agente usou ferramentas adequadamente?
        tool_score = 10.0
        expected_tools = ["buscar_produtos"]  # Sempre esperado em conversas de vendas

        if "buscar_produtos" not in tools_used:
            tool_score -= 3
            issues.append("Nao buscou produtos")

        if len(tools_used) == 0:
            tool_score -= 5
            issues.append("Nenhuma ferramenta usada")

        # Bonus por usar ferramentas uteis
        if "enviar_imagem" in tools_used:
            tool_score = min(10, tool_score + 1)
        if "calcular_financiamento" in tools_used and "financ" in conversation_goal.lower():
            tool_score = min(10, tool_score + 1)
        if "agendar_visita" in tools_used and "visita" in conversation_goal.lower():
            tool_score = min(10, tool_score + 1)

        scores["tools"] = max(0, tool_score)

        # 2. RESPONSE QUALITY (25%) - Respostas foram adequadas?
        quality_score = 10.0
        total_agent_chars = 0
        empty_responses = 0

        for turn in turn_details:
            response = turn.get("agent_response", "")
            total_agent_chars += len(response)

            if len(response) < 20:
                empty_responses += 1

            # Penalizar respostas muito curtas ou muito longas
            if len(response) < 50:
                quality_score -= 0.5
            elif len(response) > 500:
                quality_score -= 0.3

        if empty_responses > 0:
            quality_score -= empty_responses * 2
            issues.append(f"{empty_responses} resposta(s) muito curta(s)")

        # Verificar se menciona especialista/consultor (transferencia)
        last_response = turn_details[-1].get("agent_response", "") if turn_details else ""
        if "especialista" in last_response.lower() or "consultor" in last_response.lower():
            quality_score = min(10, quality_score + 1)

        scores["quality"] = max(0, quality_score)

        # 3. CONVERSATION FLOW (25%) - Fluxo foi natural?
        flow_score = 10.0

        # Verificar se coletou informacoes importantes
        all_responses = " ".join([t.get("agent_response", "") for t in turn_details]).lower()

        # Perguntas importantes que o agente deve fazer
        asked_payment = any(word in all_responses for word in ["vista", "financiar", "pagamento", "entrada"])
        asked_name = "nome" in all_responses or "qual o seu nome" in all_responses

        if not asked_payment:
            flow_score -= 2
            issues.append("Nao perguntou forma de pagamento")

        # Verificar se houve progresso na conversa
        if len(turn_details) >= 3:
            first_half_tools = []
            second_half_tools = []
            mid = len(turn_details) // 2

            for i, turn in enumerate(turn_details):
                if i < mid:
                    first_half_tools.extend(turn.get("tools_used", []))
                else:
                    second_half_tools.extend(turn.get("tools_used", []))

            # Conversa deve evoluir - mais acao na segunda metade e ok
            if len(second_half_tools) == 0 and len(first_half_tools) == 0:
                flow_score -= 2
                issues.append("Conversa sem progresso")

        scores["flow"] = max(0, flow_score)

        # 4. GOAL ACHIEVEMENT (25%) - Atingiu objetivo?
        goal_score = 10.0

        goal_lower = conversation_goal.lower()

        # Verificar se objetivo foi trabalhado
        if "financiamento" in goal_lower or "pagamento" in goal_lower:
            if "calcular_financiamento" not in tools_used and "entrada" not in all_responses:
                goal_score -= 3
                issues.append("Nao trabalhou financiamento")

        if "visita" in goal_lower or "agendar" in goal_lower:
            if "agendar_visita" not in tools_used and "visita" not in all_responses:
                goal_score -= 3
                issues.append("Nao ofereceu agendamento")

        if "foto" in goal_lower or "imagem" in goal_lower:
            if "enviar_imagem" not in tools_used:
                goal_score -= 3
                issues.append("Nao enviou fotos")

        # Verificar se conversa terminou bem (transferencia ou fechamento)
        if "consultor" in last_response.lower() or "especialista" in last_response.lower():
            goal_score = min(10, goal_score + 1)
        elif "ate mais" in last_response.lower() or "obrigad" in last_response.lower():
            pass  # OK
        else:
            goal_score -= 1

        scores["goal"] = max(0, goal_score)

        # SCORE FINAL (media ponderada)
        final_score = (
            scores["tools"] * 0.25 +
            scores["quality"] * 0.25 +
            scores["flow"] * 0.25 +
            scores["goal"] * 0.25
        )

        # Classificacao
        if final_score >= 8:
            status = "success"
        elif final_score >= 5:
            status = "warning"
        else:
            status = "error"

        return {
            "score": round(final_score, 1),
            "status": status,
            "breakdown": {
                "tools": round(scores["tools"], 1),
                "quality": round(scores["quality"], 1),
                "flow": round(scores["flow"], 1),
                "goal": round(scores["goal"], 1)
            },
            "issues": issues
        }
