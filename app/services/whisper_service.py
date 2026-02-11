import httpx
from openai import AsyncOpenAI
from typing import Optional
import logging
import io

logger = logging.getLogger(__name__)


class WhisperService:
    """Service para transcrição de áudio usando OpenAI Whisper"""

    @staticmethod
    async def transcribe_audio(
        api_key: str,
        audio_data: bytes,
        mime_type: str = "audio/ogg"
    ) -> Optional[str]:
        """Transcreve áudio usando Whisper API"""
        try:
            client = AsyncOpenAI(api_key=api_key)

            # Determinar extensão do arquivo
            extension = "ogg"
            if "mp3" in mime_type:
                extension = "mp3"
            elif "wav" in mime_type:
                extension = "wav"
            elif "m4a" in mime_type:
                extension = "m4a"
            elif "webm" in mime_type:
                extension = "webm"

            # Criar arquivo em memória
            audio_file = io.BytesIO(audio_data)
            audio_file.name = f"audio.{extension}"

            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )

            return response.text

        except Exception as e:
            logger.error(f"Erro ao transcrever áudio: {e}")
            return None

    @staticmethod
    async def download_audio(url: str) -> Optional[bytes]:
        """Baixa arquivo de áudio de uma URL"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error(f"Erro ao baixar áudio: {e}")
            return None
