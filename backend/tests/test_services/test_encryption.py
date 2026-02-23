"""
Testes para servico de encriptacao
"""
import pytest
from unittest.mock import patch
import os


def test_encrypt_decrypt():
    """Testa encriptacao e decriptacao basica"""
    # Configurar chave de teste
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()

    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        # Reimportar para usar nova chave
        from importlib import reload
        import backend.core.config
        reload(backend.core.config)

        from backend.core.encryption import EncryptionService

        service = EncryptionService()

        original = "minha-api-key-secreta"
        encrypted = service.encrypt(original)

        # Encrypted deve ser diferente do original
        assert encrypted != original

        # Decrypted deve ser igual ao original
        decrypted = service.decrypt(encrypted)
        assert decrypted == original


def test_encrypt_empty_value():
    """Testa encriptacao de valor vazio"""
    from backend.core.encryption import encryption_service

    result = encryption_service.encrypt("")
    assert result == ""

    result = encryption_service.encrypt(None)
    assert result is None


def test_is_encrypted():
    """Testa deteccao de valor encriptado"""
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()

    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        from backend.core.encryption import EncryptionService

        service = EncryptionService()

        # Valor nao encriptado
        assert service.is_encrypted("plain-text") == False
        assert service.is_encrypted("sk-12345") == False

        # Valor encriptado
        encrypted = service.encrypt("test")
        assert service.is_encrypted(encrypted) == True


def test_encrypt_if_needed():
    """Testa encriptacao condicional"""
    from cryptography.fernet import Fernet
    test_key = Fernet.generate_key().decode()

    with patch.dict(os.environ, {"ENCRYPTION_KEY": test_key}):
        from backend.core.encryption import EncryptionService

        service = EncryptionService()

        # Primeiro encriptar
        encrypted1 = service.encrypt_if_needed("test-value")
        assert service.is_encrypted(encrypted1) == True

        # Encriptar novamente nao deve alterar
        encrypted2 = service.encrypt_if_needed(encrypted1)
        assert encrypted1 == encrypted2


def test_generate_key():
    """Testa geracao de chave"""
    from backend.core.encryption import generate_key
    from cryptography.fernet import Fernet

    key = generate_key()

    # Deve ser string
    assert isinstance(key, str)

    # Deve ser valida para Fernet
    fernet = Fernet(key.encode())
    assert fernet is not None
