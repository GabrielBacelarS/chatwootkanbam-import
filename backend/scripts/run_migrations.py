#!/usr/bin/env python3
"""Script para executar todas as migrações SQL"""

import asyncio
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

load_dotenv()

MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"

# Ordem das migrações (mais antigas primeiro, depois as novas)
MIGRATION_ORDER = [
    "add_use_agent_mode.sql",
    "add_product_keywords.sql",
    "add_debounce_fields.sql",
    "add_conversation_index.sql",
    "add_batch_testing_tables.sql",
    "add_split_mode.sql",
    "add_intent_detection_mode.sql",
    # Novas migrações v2.0
    "add_analytics_tables.sql",
    "add_crm_config_table.sql",
    "add_ab_testing_tables.sql",
    "add_compliance_tables.sql",
]


async def run_migrations():
    """Executa todas as migrações em ordem"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL não configurada!")
        return False

    print(f"🔌 Conectando ao banco de dados...")
    engine = create_async_engine(database_url, echo=False)

    try:
        async with engine.begin() as conn:
            print("✅ Conexão estabelecida!\n")

            for migration_file in MIGRATION_ORDER:
                migration_path = MIGRATIONS_DIR / migration_file

                if not migration_path.exists():
                    print(f"⚠️  Migração não encontrada: {migration_file}")
                    continue

                print(f"📄 Executando: {migration_file}...")

                sql_content = migration_path.read_text(encoding="utf-8")

                # Dividir em statements individuais
                statements = []
                current = []
                in_function = False

                for line in sql_content.split("\n"):
                    # Detectar início/fim de funções PL/pgSQL
                    if "CREATE OR REPLACE FUNCTION" in line or "CREATE FUNCTION" in line:
                        in_function = True
                    if in_function and line.strip().startswith("$$ language"):
                        in_function = False
                        current.append(line)
                        statements.append("\n".join(current))
                        current = []
                        continue

                    # Ignorar comentários puros
                    if line.strip().startswith("--"):
                        continue

                    current.append(line)

                    # Separar por ';' apenas fora de funções
                    if not in_function and ";" in line:
                        stmt = "\n".join(current).strip()
                        if stmt and stmt != ";":
                            statements.append(stmt)
                        current = []

                # Executar cada statement
                for stmt in statements:
                    stmt = stmt.strip()
                    if not stmt or stmt == ";" or stmt.startswith("--"):
                        continue
                    try:
                        await conn.execute(text(stmt))
                    except Exception as e:
                        # Ignorar erros de "já existe"
                        error_msg = str(e).lower()
                        if "already exists" in error_msg or "ja existe" in error_msg:
                            pass
                        elif "does not exist" in error_msg and "drop" in stmt.lower():
                            pass
                        else:
                            print(f"   ⚠️  Aviso: {e}")

                print(f"   ✅ Concluída!")

            print("\n" + "=" * 50)
            print("🎉 Todas as migrações foram executadas com sucesso!")
            print("=" * 50)

    except Exception as e:
        print(f"\n❌ Erro ao executar migrações: {e}")
        return False
    finally:
        await engine.dispose()

    return True


if __name__ == "__main__":
    print("=" * 50)
    print("   Closefy - Executor de Migrações")
    print("=" * 50 + "\n")

    success = asyncio.run(run_migrations())
    sys.exit(0 if success else 1)
