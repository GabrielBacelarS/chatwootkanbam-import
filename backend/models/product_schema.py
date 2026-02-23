from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from backend.core.database import Base


class ProductSchema(Base):
    """
    Esquemas de produto para diferentes tipos de negocio.
    Cada schema define os campos dinamicos que um produto pode ter.
    """
    __tablename__ = "product_schemas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(50), unique=True, nullable=False)  # "vehicles", "fashion", "financing"
    name = Column(String(100), nullable=False)  # "Veiculos", "Moda", "Consorcio"
    icon = Column(String(50), default="mdi-package")  # MDI icon class
    description = Column(String(500))

    # Definicoes dos campos como JSONB array
    # Cada campo: {key, label, type, required, placeholder, group, order, options, show_in_card, show_in_rag, rag_label, rag_format}
    fields = Column(JSONB, nullable=False, default=[])

    # Configuracoes de exibicao
    card_title_field = Column(String(50), default="name")  # Campo para titulo do card
    card_subtitle_template = Column(String(200))  # Template como "{year} - {color}"
    card_price_field = Column(String(50), default="price")  # Campo para exibir preco

    # Status
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)  # Apenas um pode ser default

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "icon": self.icon,
            "description": self.description,
            "fields": self.fields or [],
            "card_title_field": self.card_title_field,
            "card_subtitle_template": self.card_subtitle_template,
            "card_price_field": self.card_price_field,
            "is_active": self.is_active,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Schemas pre-definidos para seed inicial
DEFAULT_SCHEMAS = [
    {
        "slug": "vehicles",
        "name": "Veiculos",
        "icon": "mdi-car",
        "description": "Carros, motos e outros veiculos",
        "is_default": True,
        "card_subtitle_template": "{year} - {color}",
        "fields": [
            {"key": "brand", "label": "Marca", "type": "text", "group": "identification", "order": 1, "show_in_card": True, "show_in_rag": True, "rag_label": "Marca"},
            {"key": "model", "label": "Modelo", "type": "text", "group": "identification", "order": 2, "show_in_card": True, "show_in_rag": True, "rag_label": "Modelo"},
            {"key": "year", "label": "Ano Modelo", "type": "number", "group": "identification", "order": 3, "show_in_card": True, "show_in_rag": True, "rag_label": "Ano"},
            {"key": "year_fab", "label": "Ano Fabricacao", "type": "number", "group": "identification", "order": 4, "show_in_card": False, "show_in_rag": True, "rag_label": "Ano Fab."},
            {"key": "mileage", "label": "Quilometragem", "type": "number", "placeholder": "Ex: 50000", "group": "details", "order": 5, "show_in_card": True, "show_in_rag": True, "rag_label": "Km", "rag_format": "km"},
            {"key": "color", "label": "Cor", "type": "text", "group": "details", "order": 6, "show_in_card": True, "show_in_rag": True, "rag_label": "Cor"},
            {"key": "fuel_type", "label": "Combustivel", "type": "select", "options": ["Flex", "Gasolina", "Etanol", "Diesel", "Eletrico", "Hibrido"], "group": "details", "order": 7, "show_in_card": True, "show_in_rag": True, "rag_label": "Combustivel"},
            {"key": "transmission", "label": "Cambio", "type": "select", "options": ["Manual", "Automatico", "CVT", "Automatizado"], "group": "details", "order": 8, "show_in_card": True, "show_in_rag": True, "rag_label": "Cambio"},
            {"key": "category", "label": "Categoria", "type": "text", "placeholder": "Ex: Sedan, SUV, Hatch", "group": "classification", "order": 9, "show_in_card": False, "show_in_rag": True, "rag_label": "Categoria"},
            {"key": "engine", "label": "Motor", "type": "text", "placeholder": "Ex: 2.0 Turbo", "group": "details", "order": 10, "show_in_card": False, "show_in_rag": True, "rag_label": "Motor"},
            {"key": "doors", "label": "Portas", "type": "number", "group": "details", "order": 11, "show_in_card": False, "show_in_rag": False}
        ]
    },
    {
        "slug": "fashion",
        "name": "Moda",
        "icon": "mdi-tshirt-crew",
        "description": "Roupas, calcados e acessorios",
        "is_default": False,
        "card_subtitle_template": "{brand} - {size}",
        "fields": [
            {"key": "brand", "label": "Marca", "type": "text", "group": "identification", "order": 1, "show_in_card": True, "show_in_rag": True, "rag_label": "Marca"},
            {"key": "size", "label": "Tamanho", "type": "select", "options": ["PP", "P", "M", "G", "GG", "XG", "XXG"], "group": "details", "order": 2, "show_in_card": True, "show_in_rag": True, "rag_label": "Tamanho"},
            {"key": "color", "label": "Cor", "type": "text", "group": "details", "order": 3, "show_in_card": True, "show_in_rag": True, "rag_label": "Cor"},
            {"key": "material", "label": "Material", "type": "text", "placeholder": "Ex: Algodao, Poliester", "group": "details", "order": 4, "show_in_card": False, "show_in_rag": True, "rag_label": "Material"},
            {"key": "gender", "label": "Genero", "type": "select", "options": ["Masculino", "Feminino", "Unissex", "Infantil"], "group": "classification", "order": 5, "show_in_card": True, "show_in_rag": True, "rag_label": "Genero"},
            {"key": "collection", "label": "Colecao", "type": "text", "placeholder": "Ex: Verao 2024", "group": "classification", "order": 6, "show_in_card": False, "show_in_rag": True, "rag_label": "Colecao"},
            {"key": "style", "label": "Estilo", "type": "text", "placeholder": "Ex: Casual, Esportivo", "group": "classification", "order": 7, "show_in_card": False, "show_in_rag": True, "rag_label": "Estilo"}
        ]
    },
    {
        "slug": "financing",
        "name": "Consorcio",
        "icon": "mdi-bank",
        "description": "Cartas de credito e financiamentos",
        "is_default": False,
        "card_subtitle_template": "{category} - {total_months} meses",
        "fields": [
            {"key": "credit_value", "label": "Valor da Carta", "type": "number", "required": True, "group": "values", "order": 1, "show_in_card": True, "show_in_rag": True, "rag_label": "Valor da Carta", "rag_format": "currency"},
            {"key": "monthly_fee", "label": "Parcela Mensal", "type": "number", "group": "values", "order": 2, "show_in_card": True, "show_in_rag": True, "rag_label": "Parcela", "rag_format": "currency"},
            {"key": "total_months", "label": "Prazo (meses)", "type": "number", "group": "terms", "order": 3, "show_in_card": True, "show_in_rag": True, "rag_label": "Prazo"},
            {"key": "admin_fee", "label": "Taxa Administracao (%)", "type": "number", "group": "terms", "order": 4, "show_in_card": False, "show_in_rag": True, "rag_label": "Taxa Admin"},
            {"key": "category", "label": "Categoria", "type": "select", "options": ["Imovel", "Veiculo", "Servicos", "Maquinas"], "group": "classification", "order": 5, "show_in_card": True, "show_in_rag": True, "rag_label": "Categoria"},
            {"key": "administrator", "label": "Administradora", "type": "text", "placeholder": "Ex: Porto Seguro, Embracon", "group": "identification", "order": 6, "show_in_card": True, "show_in_rag": True, "rag_label": "Administradora"},
            {"key": "contemplated", "label": "Contemplado", "type": "boolean", "group": "status", "order": 7, "show_in_card": True, "show_in_rag": True, "rag_label": "Contemplado"}
        ]
    }
]
