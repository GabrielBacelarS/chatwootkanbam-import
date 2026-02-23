"""
Script de migracao para adicionar suporte a schemas de produto.
Execute uma vez para atualizar o banco de dados existente.

Uso: python -m backend.scripts.migrate_schemas
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from backend.core.database import engine


async def migrate():
    """Executa a migracao do banco de dados"""
    print("=== Migracao de Schemas de Produto ===\n")

    async with engine.begin() as conn:
        # 1. Criar tabela product_schemas se nao existir
        print("1. Criando tabela product_schemas...")
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS product_schemas (
                id SERIAL PRIMARY KEY,
                slug VARCHAR(50) UNIQUE NOT NULL,
                name VARCHAR(100) NOT NULL,
                icon VARCHAR(50) DEFAULT 'mdi-package',
                description VARCHAR(500),
                fields JSONB NOT NULL DEFAULT '[]',
                card_title_field VARCHAR(50) DEFAULT 'name',
                card_subtitle_template VARCHAR(200),
                is_active BOOLEAN DEFAULT true,
                is_default BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """))
        print("   OK - Tabela product_schemas criada/verificada")

        # 2. Adicionar coluna product_schema_id em clients
        print("\n2. Adicionando coluna product_schema_id em clients...")
        try:
            await conn.execute(text("""
                ALTER TABLE clients
                ADD COLUMN IF NOT EXISTS product_schema_id INTEGER
                REFERENCES product_schemas(id) ON DELETE SET NULL
            """))
            print("   OK - Coluna product_schema_id adicionada")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("   OK - Coluna ja existe")
            else:
                print(f"   AVISO: {e}")

        # 3. Adicionar coluna dynamic_fields em products
        print("\n3. Adicionando coluna dynamic_fields em products...")
        try:
            await conn.execute(text("""
                ALTER TABLE products
                ADD COLUMN IF NOT EXISTS dynamic_fields JSONB DEFAULT '{}'
            """))
            print("   OK - Coluna dynamic_fields adicionada")
        except Exception as e:
            if "already exists" in str(e).lower():
                print("   OK - Coluna ja existe")
            else:
                print(f"   AVISO: {e}")

        # 4. Verificar se precisa fazer seed dos schemas default
        print("\n4. Verificando schemas default...")
        result = await conn.execute(text("SELECT COUNT(*) FROM product_schemas"))
        count = result.scalar()

        if count == 0:
            print("   Inserindo schemas padrao...")

            # Schema Veiculos
            await conn.execute(text("""
                INSERT INTO product_schemas (slug, name, icon, description, fields, card_subtitle_template, is_default)
                VALUES (
                    'vehicles',
                    'Veiculos',
                    'mdi-car',
                    'Schema para carros, motos e outros veiculos',
                    '[
                        {"key": "brand", "label": "Marca", "type": "text", "required": false, "placeholder": "Ex: Honda", "order": 1, "show_in_card": true, "show_in_rag": true, "rag_label": "Marca"},
                        {"key": "model", "label": "Modelo", "type": "text", "required": false, "placeholder": "Ex: Civic", "order": 2, "show_in_card": true, "show_in_rag": true, "rag_label": "Modelo"},
                        {"key": "year", "label": "Ano Modelo", "type": "number", "required": false, "order": 3, "show_in_card": true, "show_in_rag": true, "rag_label": "Ano"},
                        {"key": "year_fab", "label": "Ano Fabricacao", "type": "number", "required": false, "order": 4, "show_in_rag": true, "rag_label": "Fabricacao"},
                        {"key": "mileage", "label": "Quilometragem", "type": "number", "required": false, "order": 5, "show_in_card": true, "show_in_rag": true, "rag_label": "Km", "rag_format": "km"},
                        {"key": "fuel_type", "label": "Combustivel", "type": "select", "options": ["Flex", "Gasolina", "Etanol", "Diesel", "Eletrico", "Hibrido"], "order": 6, "show_in_rag": true, "rag_label": "Combustivel"},
                        {"key": "transmission", "label": "Cambio", "type": "select", "options": ["Manual", "Automatico", "CVT", "Automatizado"], "order": 7, "show_in_rag": true, "rag_label": "Cambio"},
                        {"key": "color", "label": "Cor", "type": "text", "placeholder": "Ex: Preto", "order": 8, "show_in_card": true, "show_in_rag": true, "rag_label": "Cor"},
                        {"key": "category", "label": "Categoria", "type": "text", "placeholder": "Ex: Sedan", "order": 9, "show_in_rag": true, "rag_label": "Categoria"}
                    ]'::jsonb,
                    '{year_fab}/{year} - {mileage} km - {color}',
                    true
                )
            """))
            print("   - Veiculos inserido")

            # Schema Moda
            await conn.execute(text("""
                INSERT INTO product_schemas (slug, name, icon, description, fields, card_subtitle_template)
                VALUES (
                    'fashion',
                    'Moda',
                    'mdi-tshirt-crew',
                    'Schema para roupas, calcados e acessorios',
                    '[
                        {"key": "brand", "label": "Marca", "type": "text", "placeholder": "Ex: Nike", "order": 1, "show_in_card": true, "show_in_rag": true, "rag_label": "Marca"},
                        {"key": "size", "label": "Tamanho", "type": "select", "options": ["PP", "P", "M", "G", "GG", "XG", "XXG"], "order": 2, "show_in_card": true, "show_in_rag": true, "rag_label": "Tamanho"},
                        {"key": "color", "label": "Cor", "type": "text", "placeholder": "Ex: Azul", "order": 3, "show_in_card": true, "show_in_rag": true, "rag_label": "Cor"},
                        {"key": "material", "label": "Material", "type": "text", "placeholder": "Ex: Algodao", "order": 4, "show_in_rag": true, "rag_label": "Material"},
                        {"key": "gender", "label": "Genero", "type": "select", "options": ["Masculino", "Feminino", "Unissex", "Infantil"], "order": 5, "show_in_rag": true, "rag_label": "Genero"},
                        {"key": "category", "label": "Categoria", "type": "text", "placeholder": "Ex: Camiseta", "order": 6, "show_in_rag": true, "rag_label": "Categoria"}
                    ]'::jsonb,
                    '{brand} - {size} - {color}'
                )
            """))
            print("   - Moda inserido")

            # Schema Consorcio/Financiamento
            await conn.execute(text("""
                INSERT INTO product_schemas (slug, name, icon, description, fields, card_subtitle_template)
                VALUES (
                    'financing',
                    'Consorcio/Financiamento',
                    'mdi-bank',
                    'Schema para consorcios, financiamentos e produtos financeiros',
                    '[
                        {"key": "credit_value", "label": "Valor da Carta", "type": "number", "order": 1, "show_in_card": true, "show_in_rag": true, "rag_label": "Carta de Credito", "rag_format": "currency"},
                        {"key": "monthly_fee", "label": "Parcela Mensal", "type": "number", "order": 2, "show_in_card": true, "show_in_rag": true, "rag_label": "Parcela", "rag_format": "currency"},
                        {"key": "total_months", "label": "Prazo (meses)", "type": "number", "order": 3, "show_in_card": true, "show_in_rag": true, "rag_label": "Prazo"},
                        {"key": "admin_fee", "label": "Taxa Admin (%)", "type": "number", "order": 4, "show_in_rag": true, "rag_label": "Taxa Administrativa"},
                        {"key": "category", "label": "Categoria", "type": "select", "options": ["Imovel", "Veiculo", "Servicos", "Maquinas"], "order": 5, "show_in_rag": true, "rag_label": "Categoria"},
                        {"key": "administrator", "label": "Administradora", "type": "text", "placeholder": "Ex: Embracon", "order": 6, "show_in_rag": true, "rag_label": "Administradora"}
                    ]'::jsonb,
                    'R$ {credit_value} - {total_months}x de R$ {monthly_fee}'
                )
            """))
            print("   - Consorcio/Financiamento inserido")

            print("\n   OK - Schemas padrao inseridos")
        else:
            print(f"   OK - {count} schemas ja existem")

    print("\n=== Migracao concluida com sucesso! ===")


if __name__ == "__main__":
    asyncio.run(migrate())
