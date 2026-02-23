"""
Servico para geracao automatica de casos de teste
Analisa produtos e prompt para criar testes realistas
"""
import json
import logging
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
import google.generativeai as genai

logger = logging.getLogger(__name__)


class TestGeneratorService:
    """Gera casos de teste automaticamente baseado em produtos e prompt"""

    GENERATION_PROMPT = """Voce e um especialista em criar cenarios de teste para agentes de vendas de IA.

CONTEXTO DO NEGOCIO:
{system_prompt}

PRODUTOS DISPONIVEIS NO ESTOQUE:
{products_summary}

FERRAMENTAS DO AGENTE:
{available_tools}

SUA TAREFA:
Gere {num_tests} casos de teste realistas simulando um CLIENTE REAL interessado nesses produtos.
Cada teste deve parecer uma mensagem natural que um cliente enviaria via WhatsApp.

REGRAS IMPORTANTES:
1. Use os nomes, cores, precos e caracteristicas REAIS dos produtos listados
2. Varie os tipos de perguntas: busca, preco, financiamento, fotos, agendamento
3. Inclua perguntas simples ("tem carro preto?") e complexas ("quero um carro ate 80 mil com baixa km")
4. Simule diferentes perfis de cliente: direto ao ponto, detalhista, indeciso
5. Algumas perguntas devem testar se o agente usa as ferramentas corretas
6. Inclua 1-2 perguntas "armadilha" fora do escopo para testar limites

FORMATO DE RESPOSTA (JSON):
{{
  "test_cases": [
    {{
      "name": "Nome curto do teste",
      "category": "product_search|financing|scheduling|media|greeting|out_of_scope",
      "input_message": "Mensagem que o cliente enviaria",
      "expected_tools": ["lista", "de", "tools", "esperadas"],
      "expected_keywords": ["palavras", "que", "devem", "aparecer", "na", "resposta"],
      "should_not_contain": ["palavras", "que", "NAO", "devem", "aparecer"],
      "description": "O que este teste valida"
    }}
  ]
}}

Gere exatamente {num_tests} casos de teste variados e realistas.
"""

    @staticmethod
    def _summarize_products(products: List[Dict], max_products: int = 20) -> str:
        """Resume produtos para o prompt de geracao"""
        if not products:
            return "Nenhum produto cadastrado no estoque."

        summary_lines = []
        for i, p in enumerate(products[:max_products]):
            # Extrair campos principais
            name = p.get("name", "Produto sem nome")
            price = p.get("price", 0)

            # Pegar campos extras do data
            data = p.get("data", {}) or {}
            extras = []
            for key, value in data.items():
                if value and key not in ["id", "created_at", "updated_at"]:
                    extras.append(f"{key}: {value}")

            extras_str = ", ".join(extras[:5]) if extras else ""

            line = f"- {name} | R$ {price:,.0f}"
            if extras_str:
                line += f" | {extras_str}"

            summary_lines.append(line)

        if len(products) > max_products:
            summary_lines.append(f"... e mais {len(products) - max_products} produtos")

        return "\n".join(summary_lines)

    @staticmethod
    def _get_available_tools(enabled_tools: List[str] = None) -> str:
        """Lista ferramentas disponiveis para o agente"""
        all_tools = {
            "buscar_produtos": "Busca produtos no estoque por caracteristicas",
            "calcular_financiamento": "Calcula parcelas de financiamento",
            "agendar_visita": "Agenda visitas para ver produtos",
            "enviar_imagem": "Envia fotos dos produtos",
            "encerrar_conversa": "Finaliza atendimento e transfere para humano"
        }

        if enabled_tools:
            tools = {k: v for k, v in all_tools.items() if k in enabled_tools}
        else:
            tools = all_tools

        return "\n".join([f"- {name}: {desc}" for name, desc in tools.items()])

    @staticmethod
    async def generate_with_openai(
        api_key: str,
        model: str,
        system_prompt: str,
        products: List[Dict],
        enabled_tools: List[str],
        num_tests: int = 10
    ) -> List[Dict]:
        """Gera casos de teste usando OpenAI"""
        client = AsyncOpenAI(api_key=api_key)

        prompt = TestGeneratorService.GENERATION_PROMPT.format(
            system_prompt=system_prompt or "Agente de vendas generico",
            products_summary=TestGeneratorService._summarize_products(products),
            available_tools=TestGeneratorService._get_available_tools(enabled_tools),
            num_tests=num_tests
        )

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Voce gera casos de teste em formato JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.8,  # Mais criatividade
                max_tokens=4000
            )

            content = response.choices[0].message.content
            data = json.loads(content)

            return data.get("test_cases", [])

        except Exception as e:
            logger.error(f"[TestGenerator] Erro OpenAI: {e}")
            raise

    @staticmethod
    async def generate_with_gemini(
        api_key: str,
        model: str,
        system_prompt: str,
        products: List[Dict],
        enabled_tools: List[str],
        num_tests: int = 10
    ) -> List[Dict]:
        """Gera casos de teste usando Gemini"""
        import asyncio

        genai.configure(api_key=api_key)

        prompt = TestGeneratorService.GENERATION_PROMPT.format(
            system_prompt=system_prompt or "Agente de vendas generico",
            products_summary=TestGeneratorService._summarize_products(products),
            available_tools=TestGeneratorService._get_available_tools(enabled_tools),
            num_tests=num_tests
        )

        try:
            # Gemini sync API - rodar em thread separada
            def generate_sync():
                model_instance = genai.GenerativeModel(
                    model_name=model,
                    generation_config={
                        "temperature": 0.8,
                        "response_mime_type": "application/json"
                    }
                )
                response = model_instance.generate_content(prompt)
                return response.text

            content = await asyncio.get_event_loop().run_in_executor(None, generate_sync)
            data = json.loads(content)

            return data.get("test_cases", [])

        except Exception as e:
            logger.error(f"[TestGenerator] Erro Gemini: {e}")
            raise

    @staticmethod
    async def generate_tests(
        api_key: str,
        model: str,
        system_prompt: str,
        products: List[Dict],
        enabled_tools: List[str] = None,
        num_tests: int = 10
    ) -> List[Dict]:
        """
        Gera casos de teste automaticamente.

        Args:
            api_key: Chave da API (OpenAI ou Gemini)
            model: Nome do modelo
            system_prompt: Prompt do agente
            products: Lista de produtos do estoque
            enabled_tools: Ferramentas habilitadas
            num_tests: Quantidade de testes a gerar

        Returns:
            Lista de casos de teste prontos para salvar
        """
        if "gemini" in model.lower():
            return await TestGeneratorService.generate_with_gemini(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                products=products,
                enabled_tools=enabled_tools,
                num_tests=num_tests
            )
        else:
            return await TestGeneratorService.generate_with_openai(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                products=products,
                enabled_tools=enabled_tools,
                num_tests=num_tests
            )
