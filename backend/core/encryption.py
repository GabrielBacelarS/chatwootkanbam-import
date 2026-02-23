"""
Servico de Encriptacao para dados sensiveis
Usa Fernet (AES-128-CBC) para encriptar/decriptar
"""
from typing import Optional
import logging
import base64
import os

from cryptography.fernet import Fernet, InvalidToken

from backend.core.config import settings

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Servico para encriptar e decriptar dados sensiveis (API keys, tokens, etc)

    Uso:
        encryption = EncryptionService()
        encrypted = encryption.encrypt("minha-api-key-secreta")
        decrypted = encryption.decrypt(encrypted)
    """

    def __init__(self):
        self._fernet: Optional[Fernet] = None
        self._initialize()

    def _initialize(self):
        """Inicializa o Fernet com a chave de encriptacao"""
        key = settings.encryption_key

        if not key:
            # Em desenvolvimento, gerar uma chave temporaria e avisar
            if settings.debug:
                key = Fernet.generate_key().decode()
                logger.warning(
                    "ENCRYPTION_KEY nao definida! Usando chave temporaria. "
                    "Defina ENCRYPTION_KEY no .env para producao."
                )
            else:
                # Em producao, nao inicializar sem chave
                logger.error(
                    "ENCRYPTION_KEY nao definida! Encriptacao desabilitada. "
                    "Defina ENCRYPTION_KEY no .env."
                )
                return

        try:
            # Validar que a chave e valida
            self._fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"Erro ao inicializar encriptacao: {e}")
            self._fernet = None

    @property
    def is_available(self) -> bool:
        """Verifica se encriptacao esta disponivel"""
        return self._fernet is not None

    def encrypt(self, value: str) -> str:
        """
        Encripta um valor string

        Args:
            value: Valor a ser encriptado

        Returns:
            Valor encriptado em base64

        Raises:
            ValueError: Se encriptacao nao estiver disponivel
        """
        if not value:
            return value

        if not self._fernet:
            logger.warning("Encriptacao nao disponivel, retornando valor original")
            return value

        try:
            encrypted = self._fernet.encrypt(value.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Erro ao encriptar: {e}")
            raise ValueError(f"Falha na encriptacao: {e}")

    def decrypt(self, encrypted_value: str) -> str:
        """
        Decripta um valor encriptado

        Args:
            encrypted_value: Valor encriptado em base64

        Returns:
            Valor original decriptado

        Raises:
            ValueError: Se decriptacao falhar
        """
        if not encrypted_value:
            return encrypted_value

        if not self._fernet:
            # Se nao tem fernet, assumir que o valor nao esta encriptado
            logger.warning("Encriptacao nao disponivel, retornando valor como esta")
            return encrypted_value

        try:
            decrypted = self._fernet.decrypt(encrypted_value.encode())
            return decrypted.decode()
        except InvalidToken:
            # Valor provavelmente nao esta encriptado (dados antigos)
            logger.debug("Valor nao parece estar encriptado, retornando como esta")
            return encrypted_value
        except Exception as e:
            logger.error(f"Erro ao decriptar: {e}")
            # Retornar valor original em caso de erro (compatibilidade com dados antigos)
            return encrypted_value

    def is_encrypted(self, value: str) -> bool:
        """
        Tenta determinar se um valor ja esta encriptado

        Verifica se o valor parece ser um token Fernet valido
        """
        if not value:
            return False

        try:
            # Tokens Fernet sao base64 e tem tamanho minimo
            if len(value) < 50:
                return False

            # Tentar decodificar base64
            decoded = base64.urlsafe_b64decode(value.encode())

            # Fernet tokens tem estrutura especifica (versao + timestamp + iv + ciphertext + hmac)
            # Versao e sempre 0x80
            if decoded[0] != 0x80:
                return False

            return True
        except Exception:
            return False

    def encrypt_if_needed(self, value: str) -> str:
        """
        Encripta apenas se o valor ainda nao estiver encriptado
        """
        if not value:
            return value

        if self.is_encrypted(value):
            return value

        return self.encrypt(value)


# Instancia global
encryption_service = EncryptionService()


# Helpers para uso direto
def encrypt(value: str) -> str:
    """Encripta um valor"""
    return encryption_service.encrypt(value)


def decrypt(value: str) -> str:
    """Decripta um valor"""
    return encryption_service.decrypt(value)


def encrypt_if_needed(value: str) -> str:
    """Encripta apenas se necessario"""
    return encryption_service.encrypt_if_needed(value)


def generate_key() -> str:
    """Gera uma nova chave de encriptacao"""
    return Fernet.generate_key().decode()
