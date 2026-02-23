"""
Script para executar migracoes SQL no banco de dados
Uso: python scripts/run_migration.py
"""
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

async def run_migration():
    # Pegar URL do banco e converter para asyncpg
    db_url = os.getenv("DATABASE_URL", "")

    # Converter de postgresql+asyncpg:// para postgresql://
    if "+asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    print(f"Conectando ao banco...")

    try:
        conn = await asyncpg.connect(db_url)

        # === MIGRATION 1: product_keywords ===
        print("Executando migracao: add_product_keywords...")
        await conn.execute("""
            ALTER TABLE ai_config
            ADD COLUMN IF NOT EXISTS product_keywords TEXT[] DEFAULT ARRAY[
                'produto', 'produtos', 'estoque', 'disponivel', 'disponiveis',
                'tem', 'temos', 'quais', 'preco', 'precos', 'quanto', 'valor',
                'valores', 'opcao', 'opcoes', 'ver', 'mostrar', 'conhecer', 'saber'
            ];
        """)
        print("  OK: product_keywords")

        # === MIGRATION 2: debounce_seconds em ai_config ===
        print("Executando migracao: add_debounce_seconds...")
        await conn.execute("""
            ALTER TABLE ai_config
            ADD COLUMN IF NOT EXISTS debounce_seconds DOUBLE PRECISION DEFAULT 10.0;
        """)
        print("  OK: debounce_seconds")

        # === MIGRATION 3: pending_messages em ai_conversations ===
        print("Executando migracao: add_pending_messages...")
        await conn.execute("""
            ALTER TABLE ai_conversations
            ADD COLUMN IF NOT EXISTS pending_messages JSONB DEFAULT '[]'::jsonb;
        """)
        print("  OK: pending_messages")

        # === MIGRATION 4: last_message_at em ai_conversations ===
        print("Executando migracao: add_last_message_at...")
        await conn.execute("""
            ALTER TABLE ai_conversations
            ADD COLUMN IF NOT EXISTS last_message_at DOUBLE PRECISION;
        """)
        print("  OK: last_message_at")

        print("\nTodas as migracoes executadas com sucesso!")

        await conn.close()

    except Exception as e:
        print(f"Erro: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(run_migration())
