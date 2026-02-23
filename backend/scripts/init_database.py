"""
Script para inicializar o banco de dados com tabelas e seeds
Execute: python scripts/init_database.py
"""
import asyncio
import sys
import os

# Adicionar o diretorio raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from backend.core.database import engine, Base, AsyncSessionLocal
from backend.models import Client, AIConfig, Product, ProductSchema, AIKnowledgeFile, AIConversation


async def create_tables():
    """Cria todas as tabelas"""
    print("Criando tabelas...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Tabelas criadas com sucesso!")


async def seed_product_schemas():
    """Cria schemas de produto padrão"""
    print("Criando schemas de produto...")

    async with AsyncSessionLocal() as db:
        # Verificar se já existem schemas
        result = await db.execute(text("SELECT COUNT(*) FROM product_schemas"))
        count = result.scalar()

        if count > 0:
            print(f"Ja existem {count} schemas. Pulando seeds.")
            return

        # Schema: Veiculos
        vehicles_schema = ProductSchema(
            slug="vehicles",
            name="Veiculos",
            icon="mdi-car",
            description="Schema para veiculos (carros, motos, caminhoes)",
            is_active=True,
            is_default=True,
            card_title_field="name",
            card_subtitle_template="{year} - {color}",
            fields=[
                {"key": "brand", "label": "Marca", "type": "text", "required": True, "order": 1, "show_in_card": True, "show_in_rag": True, "rag_label": "Marca"},
                {"key": "model", "label": "Modelo", "type": "text", "required": True, "order": 2, "show_in_card": True, "show_in_rag": True, "rag_label": "Modelo"},
                {"key": "year", "label": "Ano Modelo", "type": "number", "required": False, "order": 3, "show_in_card": True, "show_in_rag": True, "rag_label": "Ano"},
                {"key": "year_fab", "label": "Ano Fabricacao", "type": "number", "required": False, "order": 4, "show_in_card": False, "show_in_rag": True, "rag_label": "Fabricacao"},
                {"key": "mileage", "label": "Quilometragem", "type": "number", "required": False, "order": 5, "show_in_card": True, "show_in_rag": True, "rag_label": "Km", "rag_format": "km"},
                {"key": "fuel_type", "label": "Combustivel", "type": "select", "required": False, "order": 6, "options": ["Flex", "Gasolina", "Diesel", "Eletrico", "Hibrido"], "show_in_card": True, "show_in_rag": True, "rag_label": "Combustivel"},
                {"key": "transmission", "label": "Cambio", "type": "select", "required": False, "order": 7, "options": ["Manual", "Automatico", "CVT", "Automatizado"], "show_in_card": True, "show_in_rag": True, "rag_label": "Cambio"},
                {"key": "color", "label": "Cor", "type": "text", "required": False, "order": 8, "show_in_card": True, "show_in_rag": True, "rag_label": "Cor"},
                {"key": "doors", "label": "Portas", "type": "select", "required": False, "order": 9, "options": ["2", "4"], "show_in_card": False, "show_in_rag": True, "rag_label": "Portas"},
                {"key": "engine", "label": "Motor", "type": "text", "required": False, "order": 10, "show_in_card": False, "show_in_rag": True, "rag_label": "Motor"},
            ]
        )
        db.add(vehicles_schema)

        # Schema: Moda
        fashion_schema = ProductSchema(
            slug="fashion",
            name="Moda",
            icon="mdi-tshirt-crew",
            description="Schema para roupas e acessorios",
            is_active=True,
            is_default=False,
            card_title_field="name",
            card_subtitle_template="{brand} - {size}",
            fields=[
                {"key": "brand", "label": "Marca", "type": "text", "required": False, "order": 1, "show_in_card": True, "show_in_rag": True, "rag_label": "Marca"},
                {"key": "size", "label": "Tamanho", "type": "select", "required": False, "order": 2, "options": ["PP", "P", "M", "G", "GG", "XG", "XXG"], "show_in_card": True, "show_in_rag": True, "rag_label": "Tamanho"},
                {"key": "color", "label": "Cor", "type": "text", "required": False, "order": 3, "show_in_card": True, "show_in_rag": True, "rag_label": "Cor"},
                {"key": "material", "label": "Material", "type": "text", "required": False, "order": 4, "show_in_card": False, "show_in_rag": True, "rag_label": "Material"},
                {"key": "gender", "label": "Genero", "type": "select", "required": False, "order": 5, "options": ["Masculino", "Feminino", "Unissex", "Infantil"], "show_in_card": True, "show_in_rag": True, "rag_label": "Genero"},
                {"key": "category", "label": "Categoria", "type": "select", "required": False, "order": 6, "options": ["Camiseta", "Calca", "Vestido", "Saia", "Jaqueta", "Acessorio"], "show_in_card": True, "show_in_rag": True, "rag_label": "Categoria"},
            ]
        )
        db.add(fashion_schema)

        # Schema: Consorcio/Financiamento
        financing_schema = ProductSchema(
            slug="financing",
            name="Consorcio",
            icon="mdi-bank",
            description="Schema para consorcios e financiamentos",
            is_active=True,
            is_default=False,
            card_title_field="name",
            card_subtitle_template="{category} - {total_months}x",
            fields=[
                {"key": "credit_value", "label": "Valor da Carta", "type": "number", "required": True, "order": 1, "show_in_card": True, "show_in_rag": True, "rag_label": "Valor da Carta", "rag_format": "currency"},
                {"key": "monthly_fee", "label": "Parcela Mensal", "type": "number", "required": True, "order": 2, "show_in_card": True, "show_in_rag": True, "rag_label": "Parcela", "rag_format": "currency"},
                {"key": "total_months", "label": "Prazo (meses)", "type": "number", "required": False, "order": 3, "show_in_card": True, "show_in_rag": True, "rag_label": "Prazo"},
                {"key": "admin_fee", "label": "Taxa Admin (%)", "type": "number", "required": False, "order": 4, "show_in_card": False, "show_in_rag": True, "rag_label": "Taxa Admin"},
                {"key": "category", "label": "Categoria", "type": "select", "required": False, "order": 5, "options": ["Imovel", "Veiculo", "Servicos", "Moto"], "show_in_card": True, "show_in_rag": True, "rag_label": "Categoria"},
                {"key": "administrator", "label": "Administradora", "type": "text", "required": False, "order": 6, "show_in_card": True, "show_in_rag": True, "rag_label": "Administradora"},
            ]
        )
        db.add(financing_schema)

        # Schema: Imoveis
        realestate_schema = ProductSchema(
            slug="realestate",
            name="Imoveis",
            icon="mdi-home",
            description="Schema para imoveis (casas, apartamentos, terrenos)",
            is_active=True,
            is_default=False,
            card_title_field="name",
            card_subtitle_template="{bedrooms} quartos - {area}m²",
            fields=[
                {"key": "property_type", "label": "Tipo", "type": "select", "required": True, "order": 1, "options": ["Casa", "Apartamento", "Terreno", "Sala Comercial", "Galpao"], "show_in_card": True, "show_in_rag": True, "rag_label": "Tipo"},
                {"key": "area", "label": "Area (m²)", "type": "number", "required": False, "order": 2, "show_in_card": True, "show_in_rag": True, "rag_label": "Area", "rag_format": "number"},
                {"key": "bedrooms", "label": "Quartos", "type": "number", "required": False, "order": 3, "show_in_card": True, "show_in_rag": True, "rag_label": "Quartos"},
                {"key": "bathrooms", "label": "Banheiros", "type": "number", "required": False, "order": 4, "show_in_card": True, "show_in_rag": True, "rag_label": "Banheiros"},
                {"key": "parking", "label": "Vagas", "type": "number", "required": False, "order": 5, "show_in_card": True, "show_in_rag": True, "rag_label": "Vagas"},
                {"key": "neighborhood", "label": "Bairro", "type": "text", "required": False, "order": 6, "show_in_card": True, "show_in_rag": True, "rag_label": "Bairro"},
                {"key": "city", "label": "Cidade", "type": "text", "required": False, "order": 7, "show_in_card": True, "show_in_rag": True, "rag_label": "Cidade"},
            ]
        )
        db.add(realestate_schema)

        await db.commit()
        print("4 schemas de produto criados: vehicles, fashion, financing, realestate")


async def main():
    print("=" * 50)
    print("INICIALIZACAO DO BANCO DE DADOS")
    print("=" * 50)

    try:
        await create_tables()
        await seed_product_schemas()
        print("\n" + "=" * 50)
        print("BANCO INICIALIZADO COM SUCESSO!")
        print("=" * 50)
    except Exception as e:
        print(f"\nERRO: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
