import httpx
import base64
from openai import AsyncOpenAI
import google.generativeai as genai
from typing import Optional, List, Dict
import logging

logger = logging.getLogger(__name__)


class AIService:
    """Service para interação com provedores de IA (OpenAI e Gemini)"""

    @staticmethod
    async def call_openai(
        api_key: str,
        messages: List[Dict],
        model: str = "gpt-4o-mini",
        system_prompt: Optional[str] = None
    ) -> str:
        """Chama a API da OpenAI"""
        try:
            client = AsyncOpenAI(api_key=api_key)

            # Preparar mensagens
            formatted_messages = []
            if system_prompt:
                formatted_messages.append({"role": "system", "content": system_prompt})

            for msg in messages:
                formatted_messages.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", "")
                })

            response = await client.chat.completions.create(
                model=model,
                messages=formatted_messages,
                temperature=0.7,
                max_tokens=2000
            )

            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"Erro ao chamar OpenAI: {e}")
            raise

    @staticmethod
    async def call_gemini(
        api_key: str,
        messages: List[Dict],
        model: str = "gemini-1.5-flash",
        system_prompt: Optional[str] = None
    ) -> str:
        """Chama a API do Google Gemini"""
        try:
            genai.configure(api_key=api_key)

            # Construir prompt completo
            full_prompt = ""
            if system_prompt:
                full_prompt = f"Instruções do sistema: {system_prompt}\n\n"

            # Adicionar histórico
            for msg in messages:
                role = "Usuário" if msg.get("role") == "user" else "Assistente"
                full_prompt += f"{role}: {msg.get('content', '')}\n"

            full_prompt += "Assistente:"

            # Chamar Gemini
            model_instance = genai.GenerativeModel(model)
            response = await model_instance.generate_content_async(full_prompt)

            return response.text or ""

        except Exception as e:
            logger.error(f"Erro ao chamar Gemini: {e}")
            raise

    @staticmethod
    async def generate_response(
        provider: str,
        api_key: str,
        messages: List[Dict],
        model: str,
        system_prompt: Optional[str] = None,
        knowledge_base: Optional[str] = None
    ) -> str:
        """Gera resposta usando o provedor configurado"""

        # Adicionar base de conhecimento ao system prompt
        full_system_prompt = system_prompt or "Você é um assistente virtual prestativo."
        if knowledge_base:
            full_system_prompt += f"\n\n=== BASE DE CONHECIMENTO ===\n{knowledge_base}"

        if provider == "openai":
            return await AIService.call_openai(
                api_key=api_key,
                messages=messages,
                model=model,
                system_prompt=full_system_prompt
            )
        elif provider == "gemini":
            return await AIService.call_gemini(
                api_key=api_key,
                messages=messages,
                model=model,
                system_prompt=full_system_prompt
            )
        else:
            raise ValueError(f"Provedor de IA não suportado: {provider}")

    @staticmethod
    async def analyze_image(
        api_key: str,
        image_url: str,
        context: str = "produto"
    ) -> str:
        """
        Analisa uma imagem usando GPT-4 Vision e retorna descricao do que ve.
        Usado para identificar produtos quando cliente envia foto.
        """
        try:
            client = AsyncOpenAI(api_key=api_key)

            # Baixar a imagem e converter para base64
            async with httpx.AsyncClient(timeout=30.0) as http_client:
                response = await http_client.get(image_url, follow_redirects=True)
                response.raise_for_status()
                image_data = base64.b64encode(response.content).decode('utf-8')
                content_type = response.headers.get("content-type", "image/jpeg")

            # Prompt para analise de produto
            analysis_prompt = f"""Analise esta imagem e descreva o {context} que voce ve.

Se for um VEICULO, identifique:
- Marca e modelo (se possivel)
- Cor
- Tipo (sedan, hatch, SUV, pickup, etc)
- Caracteristicas visiveis

Se for outro tipo de produto, descreva:
- Tipo/categoria do produto
- Marca (se visivel)
- Cor/caracteristicas principais

Responda de forma BREVE e OBJETIVA, em uma ou duas frases.
Exemplo: "Renault Sandero branco, modelo hatch compacto"
Exemplo: "Ar condicionado split LG, cor branca, aparenta ser 12000 BTUs"

Se NAO conseguir identificar o produto na imagem, diga "Nao consegui identificar o produto na imagem"."""

            response = await client.chat.completions.create(
                model="gpt-4o",  # Modelo com visao
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": analysis_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{content_type};base64,{image_data}",
                                    "detail": "low"  # Usar low para economizar tokens
                                }
                            }
                        ]
                    }
                ],
                max_tokens=150
            )

            result = response.choices[0].message.content or ""
            logger.info(f"Analise de imagem: {result}")
            return result

        except Exception as e:
            logger.error(f"Erro ao analisar imagem: {e}")
            return ""

    @staticmethod
    async def summarize_conversation(
        api_key: str,
        messages: List[Dict],
        provider: str = "openai",
        model: str = "gpt-4o-mini"
    ) -> str:
        """
        Gera um resumo da conversa para handoff ao atendente humano.
        Retorna um resumo estruturado com informacoes relevantes.
        """
        if not messages:
            return "Nenhuma mensagem na conversa."

        # Construir historico formatado
        conversation_text = ""
        for msg in messages[-20:]:  # Ultimas 20 mensagens
            role = "Cliente" if msg.get("role") == "user" else "IA"
            content = msg.get("content", "")[:500]  # Limitar tamanho
            conversation_text += f"{role}: {content}\n"

        summary_prompt = """Voce e um assistente que gera resumos de conversas para atendentes humanos.

Analise a conversa abaixo e gere um resumo BREVE e UTIL contendo:
1. **Motivo do contato**: O que o cliente quer?
2. **Produtos de interesse**: Quais produtos/servicos foram mencionados?
3. **Informacoes do cliente**: Nome, preferencias, restricoes mencionadas
4. **Status**: O que ja foi feito/informado pela IA?
5. **Proximo passo**: O que o atendente deve fazer?

IMPORTANTE: Seja direto e objetivo. Maximo 5-6 linhas.

=== CONVERSA ===
""" + conversation_text

        try:
            if provider == "openai":
                return await AIService.call_openai(
                    api_key=api_key,
                    messages=[{"role": "user", "content": summary_prompt}],
                    model=model
                )
            elif provider == "gemini":
                return await AIService.call_gemini(
                    api_key=api_key,
                    messages=[{"role": "user", "content": summary_prompt}],
                    model=model
                )
            else:
                return "Resumo nao disponivel (provedor nao suportado)"
        except Exception as e:
            logger.error(f"Erro ao gerar resumo: {e}")
            return f"Erro ao gerar resumo: {str(e)}"

    @staticmethod
    def split_message(
        text: str,
        max_length: int = 1000,
        split_by_paragraph: bool = True,
        split_mode: str = "smart"
    ) -> List[str]:
        """
        Divide mensagem em partes menores de forma inteligente.

        Modos:
        - "none": Sem quebra (mensagem unica, ignora max_length)
        - "paragraph": Quebra apenas por paragrafos
        - "sentence": Quebra por sentencas (pontos finais)
        - "character": Quebra apenas por limite de caracteres
        - "smart": Inteligente (paragrafos > sentencas > palavras)
        """
        import re

        if not text:
            return []

        # Modo "none" - sem quebra
        if split_mode == "none":
            return [text]

        # Garantir max_length minimo
        max_length = max(max_length, 100)

        # Se o texto cabe inteiro, retorna como esta
        if len(text) <= max_length:
            return [text]

        parts = []

        # Modo "character" - quebra simples por limite
        if split_mode == "character":
            return AIService._split_by_words(text, max_length)

        # Modo "sentence" - quebra por sentencas
        if split_mode == "sentence":
            return AIService._split_by_sentences(text, max_length)

        # Modo "paragraph" - quebra apenas por paragrafos (sem fallback para sentencas)
        if split_mode == "paragraph":
            # Normaliza quebras de linha
            normalized = re.sub(r'\n\s*\n', '\n\n', text)
            paragraphs = [p.strip() for p in normalized.split('\n\n') if p.strip()]

            # Se nao houver paragrafos, tentar quebra simples
            if len(paragraphs) <= 1:
                paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

            # Retorna cada paragrafo como uma mensagem separada
            return paragraphs if paragraphs else [text]

        # Modo "smart" (padrao) - dividir inteligentemente
        # Dividir por paragrafos (dupla quebra de linha ou quebra simples)
        if split_by_paragraph:
            # Normaliza quebras de linha
            normalized = re.sub(r'\n\s*\n', '\n\n', text)  # Normaliza paragrafos
            paragraphs = [p.strip() for p in normalized.split('\n\n') if p.strip()]

            # Se nao houver paragrafos, tentar quebra simples
            if len(paragraphs) <= 1:
                paragraphs = [p.strip() for p in text.split('\n') if p.strip()]

            current_part = ""

            for para in paragraphs:
                # Se o paragrafo sozinho e maior que max_length, quebrar
                if len(para) > max_length:
                    # Salvar parte atual se houver
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = ""
                    # Quebrar paragrafo grande por sentencas
                    sub_parts = AIService._split_by_sentences(para, max_length)
                    parts.extend(sub_parts)
                # Se cabe na parte atual
                elif len(current_part) + len(para) + 2 <= max_length:
                    if current_part:
                        current_part += "\n\n" + para
                    else:
                        current_part = para
                # Nao cabe, salvar atual e iniciar nova
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = para

            # Salvar ultima parte
            if current_part:
                parts.append(current_part.strip())

        else:
            # Nao dividir por paragrafo, dividir por sentencas
            parts = AIService._split_by_sentences(text, max_length)

        return parts if parts else [text]

    @staticmethod
    def _split_by_sentences(text: str, max_length: int) -> List[str]:
        """Divide texto por sentencas"""
        import re

        # Regex para quebrar em sentencas (apos pontuacao seguida de espaco)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        parts = []
        current = ""

        for sentence in sentences:
            # Se a sentenca sozinha e maior que max_length
            if len(sentence) > max_length:
                if current:
                    parts.append(current.strip())
                    current = ""
                # Dividir por palavras
                word_parts = AIService._split_by_words(sentence, max_length)
                parts.extend(word_parts)
            # Se cabe na parte atual
            elif len(current) + len(sentence) + 1 <= max_length:
                if current:
                    current += " " + sentence
                else:
                    current = sentence
            # Nao cabe
            else:
                if current:
                    parts.append(current.strip())
                current = sentence

        if current:
            parts.append(current.strip())

        return parts

    @staticmethod
    def _split_by_words(text: str, max_length: int) -> List[str]:
        """Divide texto por palavras como último recurso"""
        words = text.split()
        parts = []
        current_part = ""

        for word in words:
            # Se uma palavra sozinha excede o limite, dividir a palavra
            if len(word) > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = ""
                # Dividir palavra por caracteres
                while len(word) > max_length:
                    parts.append(word[:max_length])
                    word = word[max_length:]
                if word:
                    current_part = word
                continue

            test_part = f"{current_part} {word}" if current_part else word

            if len(test_part) <= max_length:
                current_part = test_part
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = word

        if current_part:
            parts.append(current_part.strip())

        return parts
