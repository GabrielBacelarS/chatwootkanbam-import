"""
Channel Adapter Service - Adapta mensagens para diferentes canais
"""
from typing import Optional, List, Dict, Any
from enum import Enum
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


class Channel(str, Enum):
    """Canais suportados"""
    WHATSAPP = "whatsapp"
    SMS = "sms"
    WEB = "web"
    TELEGRAM = "telegram"
    EMAIL = "email"


@dataclass
class ChannelConfig:
    """Configuracao de canal"""
    max_length: int
    supports_markdown: bool
    supports_emojis: bool
    supports_images: bool
    supports_links: bool
    line_break: str = "\n"


# Configuracoes por canal
CHANNEL_CONFIGS: Dict[Channel, ChannelConfig] = {
    Channel.WHATSAPP: ChannelConfig(
        max_length=4096,
        supports_markdown=True,
        supports_emojis=True,
        supports_images=True,
        supports_links=True
    ),
    Channel.SMS: ChannelConfig(
        max_length=160,
        supports_markdown=False,
        supports_emojis=False,  # Alguns carriers suportam, mas melhor evitar
        supports_images=False,
        supports_links=True  # Links curtos funcionam
    ),
    Channel.WEB: ChannelConfig(
        max_length=10000,  # Praticamente ilimitado
        supports_markdown=True,
        supports_emojis=True,
        supports_images=True,
        supports_links=True
    ),
    Channel.TELEGRAM: ChannelConfig(
        max_length=4096,
        supports_markdown=True,
        supports_emojis=True,
        supports_images=True,
        supports_links=True
    ),
    Channel.EMAIL: ChannelConfig(
        max_length=50000,
        supports_markdown=True,
        supports_emojis=True,
        supports_images=True,
        supports_links=True
    )
}


class ChannelAdapterService:
    """Servico para adaptar mensagens a diferentes canais"""

    @staticmethod
    def detect_channel(inbox_name: str = None, channel_type: str = None) -> Channel:
        """
        Detecta o canal baseado no nome da inbox ou tipo.

        Args:
            inbox_name: Nome da inbox no Chatwoot
            channel_type: Tipo de canal do Chatwoot

        Returns:
            Canal detectado
        """
        # Detectar por tipo de canal
        if channel_type:
            channel_type_lower = channel_type.lower()
            if "whatsapp" in channel_type_lower or "api_whatsapp" in channel_type_lower:
                return Channel.WHATSAPP
            elif "sms" in channel_type_lower or "twilio" in channel_type_lower:
                return Channel.SMS
            elif "telegram" in channel_type_lower:
                return Channel.TELEGRAM
            elif "email" in channel_type_lower:
                return Channel.EMAIL
            elif "web" in channel_type_lower or "widget" in channel_type_lower:
                return Channel.WEB

        # Detectar por nome da inbox
        if inbox_name:
            inbox_lower = inbox_name.lower()
            if "whatsapp" in inbox_lower or "wpp" in inbox_lower or "zap" in inbox_lower:
                return Channel.WHATSAPP
            elif "sms" in inbox_lower:
                return Channel.SMS
            elif "telegram" in inbox_lower or "tg" in inbox_lower:
                return Channel.TELEGRAM
            elif "email" in inbox_lower or "mail" in inbox_lower:
                return Channel.EMAIL
            elif "web" in inbox_lower or "site" in inbox_lower or "chat" in inbox_lower:
                return Channel.WEB

        # Default: WhatsApp (mais comum)
        return Channel.WHATSAPP

    @staticmethod
    def adapt_message(
        message: str,
        channel: Channel,
        preserve_formatting: bool = True
    ) -> str:
        """
        Adapta mensagem para um canal especifico.

        Args:
            message: Mensagem original
            channel: Canal de destino
            preserve_formatting: Tentar preservar formatacao quando possivel

        Returns:
            Mensagem adaptada
        """
        config = CHANNEL_CONFIGS.get(channel, CHANNEL_CONFIGS[Channel.WHATSAPP])

        # Remover markdown se canal nao suporta
        if not config.supports_markdown:
            message = ChannelAdapterService._remove_markdown(message)

        # Remover emojis se canal nao suporta
        if not config.supports_emojis:
            message = ChannelAdapterService._remove_emojis(message)

        # Truncar se necessario
        if len(message) > config.max_length:
            message = ChannelAdapterService._truncate_message(
                message,
                config.max_length
            )

        # Adaptar quebras de linha
        message = message.replace("\n", config.line_break)

        return message

    @staticmethod
    def split_for_channel(
        message: str,
        channel: Channel
    ) -> List[str]:
        """
        Divide mensagem em partes que cabem no canal.

        Args:
            message: Mensagem original
            channel: Canal de destino

        Returns:
            Lista de partes da mensagem
        """
        config = CHANNEL_CONFIGS.get(channel, CHANNEL_CONFIGS[Channel.WHATSAPP])
        max_length = config.max_length

        if len(message) <= max_length:
            return [message]

        parts = []
        current_part = ""

        # Dividir por paragrafos primeiro
        paragraphs = message.split("\n\n")

        for paragraph in paragraphs:
            # Se paragrafo cabe na parte atual
            if len(current_part) + len(paragraph) + 2 <= max_length:
                if current_part:
                    current_part += "\n\n"
                current_part += paragraph
            else:
                # Salvar parte atual se existe
                if current_part:
                    parts.append(current_part.strip())
                    current_part = ""

                # Se paragrafo e muito grande, dividir por frases
                if len(paragraph) > max_length:
                    sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                    for sentence in sentences:
                        if len(current_part) + len(sentence) + 1 <= max_length:
                            if current_part:
                                current_part += " "
                            current_part += sentence
                        else:
                            if current_part:
                                parts.append(current_part.strip())
                            current_part = sentence
                else:
                    current_part = paragraph

        # Adicionar ultima parte
        if current_part:
            parts.append(current_part.strip())

        return parts

    @staticmethod
    def _remove_markdown(text: str) -> str:
        """Remove formatacao markdown"""
        # Bold **text** ou __text__
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'__(.*?)__', r'\1', text)

        # Italic *text* ou _text_
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = re.sub(r'_(.*?)_', r'\1', text)

        # Strikethrough ~~text~~
        text = re.sub(r'~~(.*?)~~', r'\1', text)

        # Code `text`
        text = re.sub(r'`(.*?)`', r'\1', text)

        # Links [text](url) -> text (url)
        text = re.sub(r'\[(.*?)\]\((.*?)\)', r'\1 (\2)', text)

        # Headers # ## ###
        text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)

        # Listas - * +
        text = re.sub(r'^\s*[-*+]\s+', '• ', text, flags=re.MULTILINE)

        return text

    @staticmethod
    def _remove_emojis(text: str) -> str:
        """Remove emojis do texto"""
        # Pattern para emojis Unicode
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # Emoticons
            "\U0001F300-\U0001F5FF"  # Symbols & pictographs
            "\U0001F680-\U0001F6FF"  # Transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # Flags
            "\U00002702-\U000027B0"  # Dingbats
            "\U000024C2-\U0001F251"  # Enclosed characters
            "\U0001F900-\U0001F9FF"  # Supplemental Symbols
            "\U0001FA00-\U0001FA6F"  # Chess Symbols
            "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
            "]+",
            flags=re.UNICODE
        )
        return emoji_pattern.sub('', text)

    @staticmethod
    def _truncate_message(text: str, max_length: int, suffix: str = "...") -> str:
        """Trunca mensagem de forma inteligente"""
        if len(text) <= max_length:
            return text

        # Reservar espaco para sufixo
        target_length = max_length - len(suffix)

        # Tentar truncar em frase
        last_sentence = text[:target_length].rfind('. ')
        if last_sentence > target_length * 0.7:  # Se frase termina apos 70%
            return text[:last_sentence + 1]

        # Truncar em palavra
        last_space = text[:target_length].rfind(' ')
        if last_space > target_length * 0.8:  # Se palavra termina apos 80%
            return text[:last_space] + suffix

        # Truncar simples
        return text[:target_length] + suffix

    @staticmethod
    def format_for_channel(
        message: str,
        channel: Channel,
        add_signature: bool = False,
        signature: str = None
    ) -> str:
        """
        Formata mensagem completamente para um canal.

        Args:
            message: Mensagem original
            channel: Canal de destino
            add_signature: Adicionar assinatura
            signature: Assinatura customizada

        Returns:
            Mensagem formatada
        """
        # Adaptar mensagem
        formatted = ChannelAdapterService.adapt_message(message, channel)

        # Adicionar assinatura se solicitado
        if add_signature:
            config = CHANNEL_CONFIGS.get(channel, CHANNEL_CONFIGS[Channel.WHATSAPP])

            if signature:
                sig = signature
            else:
                sig = "🤖 Closefy AI" if config.supports_emojis else "- Closefy AI"

            # Verificar se cabe
            if len(formatted) + len(sig) + 2 <= config.max_length:
                formatted = f"{formatted}\n\n{sig}"

        return formatted

    @staticmethod
    def get_channel_info(channel: Channel) -> Dict[str, Any]:
        """Retorna informacoes sobre um canal"""
        config = CHANNEL_CONFIGS.get(channel, CHANNEL_CONFIGS[Channel.WHATSAPP])

        return {
            "channel": channel.value,
            "max_length": config.max_length,
            "supports_markdown": config.supports_markdown,
            "supports_emojis": config.supports_emojis,
            "supports_images": config.supports_images,
            "supports_links": config.supports_links
        }
