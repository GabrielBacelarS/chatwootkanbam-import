"""
Script para encriptar API keys existentes no banco de dados

Execute com: python scripts/encrypt_existing_keys.py

IMPORTANTE: Defina ENCRYPTION_KEY no .env antes de executar!
"""
import asyncio
import sys
import os

# Adicionar diretorio pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from backend.core.database import AsyncSessionLocal, engine
from backend.core.encryption import encryption_service, encrypt_if_needed
from backend.core.config import settings


async def encrypt_ai_config_keys():
    """Encripta api_key e openai_key_for_whisper em ai_config"""
    print("Encriptando API keys em ai_config...")

    async with AsyncSessionLocal() as db:
        # Buscar todos os registros
        result = await db.execute(
            select("*").select_from("ai_config")
        )

        # SQLAlchemy retorna RowMapping, precisamos usar text query
        from sqlalchemy import text

        result = await db.execute(text("SELECT id, api_key, openai_key_for_whisper FROM ai_config"))
        rows = result.fetchall()

        count = 0
        for row in rows:
            id_, api_key, whisper_key = row

            updates = {}

            # Encriptar api_key se existir e nao estiver encriptada
            if api_key and not encryption_service.is_encrypted(api_key):
                updates["api_key"] = encrypt_if_needed(api_key)

            # Encriptar openai_key_for_whisper se existir e nao estiver encriptada
            if whisper_key and not encryption_service.is_encrypted(whisper_key):
                updates["openai_key_for_whisper"] = encrypt_if_needed(whisper_key)

            if updates:
                # Construir query de update
                set_clause = ", ".join([f"{k} = :val_{k}" for k in updates.keys()])
                params = {f"val_{k}": v for k, v in updates.items()}
                params["id"] = id_

                await db.execute(
                    text(f"UPDATE ai_config SET {set_clause} WHERE id = :id"),
                    params
                )
                count += 1
                print(f"  Encriptado ai_config id={id_}")

        await db.commit()
        print(f"Total de registros atualizados em ai_config: {count}")


async def encrypt_client_tokens():
    """Encripta api_token em clients"""
    print("Encriptando API tokens em clients...")

    async with AsyncSessionLocal() as db:
        from sqlalchemy import text

        result = await db.execute(text("SELECT slug, api_token FROM clients"))
        rows = result.fetchall()

        count = 0
        for row in rows:
            slug, api_token = row

            # Encriptar api_token se existir e nao estiver encriptado
            if api_token and not encryption_service.is_encrypted(api_token):
                encrypted = encrypt_if_needed(api_token)

                await db.execute(
                    text("UPDATE clients SET api_token = :token WHERE slug = :slug"),
                    {"token": encrypted, "slug": slug}
                )
                count += 1
                print(f"  Encriptado client slug={slug}")

        await db.commit()
        print(f"Total de registros atualizados em clients: {count}")


async def main():
    print("=" * 60)
    print("Script de Encriptacao de API Keys")
    print("=" * 60)

    # Verificar se ENCRYPTION_KEY esta definida
    if not settings.encryption_key:
        print("\nERRO: ENCRYPTION_KEY nao definida no .env!")
        print("Gere uma chave com:")
        print('  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"')
        print("\nAdicione ao .env:")
        print("  ENCRYPTION_KEY=sua-chave-aqui")
        return

    if not encryption_service.is_available:
        print("\nERRO: Servico de encriptacao nao disponivel!")
        return

    print(f"\nUsando banco: {settings.database_url[:50]}...")
    print("")

    try:
        await encrypt_ai_config_keys()
        print("")
        await encrypt_client_tokens()
        print("")
        print("=" * 60)
        print("Encriptacao concluida com sucesso!")
        print("=" * 60)
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
