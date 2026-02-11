import httpx
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
    def split_message(
        text: str,
        max_length: int = 1000,
        split_by_paragraph: bool = True
    ) -> List[str]:
        """Divide mensagem em partes menores de forma inteligente"""
        if len(text) <= max_length:
            return [text]

        parts = []

        if split_by_paragraph:
            # Dividir por parágrafos primeiro
            paragraphs = text.split("\n\n")
            current_part = ""

            for paragraph in paragraphs:
                if len(current_part) + len(paragraph) + 2 <= max_length:
                    current_part += ("\n\n" if current_part else "") + paragraph
                else:
                    if current_part:
                        parts.append(current_part.strip())
                    # Se o parágrafo é maior que o máximo, dividir por caracteres
                    if len(paragraph) > max_length:
                        while len(paragraph) > max_length:
                            parts.append(paragraph[:max_length])
                            paragraph = paragraph[max_length:]
                        current_part = paragraph
                    else:
                        current_part = paragraph

            if current_part:
                parts.append(current_part.strip())
        else:
            # Dividir por caracteres
            while len(text) > max_length:
                parts.append(text[:max_length])
                text = text[max_length:]
            if text:
                parts.append(text)

        return parts
