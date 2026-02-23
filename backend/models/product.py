from sqlalchemy import Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from backend.core.database import Base


class Product(Base):
    """Modelo para produtos na base de conhecimento (carros, etc.)"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"))

    # Identificação
    name = Column(String(255), nullable=False)  # Ex: "Honda Civic 2023"
    code = Column(String(100))  # Código interno ou placa
    category = Column(String(100))  # Ex: "Sedan", "SUV", "Hatch"
    brand = Column(String(100))  # Ex: "Honda", "Toyota"
    model = Column(String(100))  # Ex: "Civic", "Corolla"
    year = Column(Integer)  # Ano do modelo
    year_fab = Column(Integer)  # Ano de fabricação

    # Preços
    price = Column(Float)  # Preço de venda
    price_fipe = Column(Float)  # Preço FIPE
    price_promo = Column(Float)  # Preço promocional

    # Descrição
    description = Column(Text)  # Descrição completa
    short_description = Column(String(500))  # Descrição curta
    features = Column(ARRAY(String))  # Lista de características
    specifications = Column(JSONB)  # Especificações técnicas em JSON

    # Campos dinamicos baseados no schema do cliente
    dynamic_fields = Column(JSONB, default={})

    # Imagens (armazenadas no MinIO)
    main_image = Column(String(500))  # Caminho da imagem principal no MinIO
    images = Column(ARRAY(String))  # Lista de caminhos de imagens adicionais
    video_url = Column(String(500))  # URL do vídeo (YouTube, etc.)

    # Status
    is_available = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # Destaque
    stock_quantity = Column(Integer, default=1)

    # Localização
    location = Column(String(255))  # Localização do produto

    # Veículos específicos
    mileage = Column(Integer)  # Quilometragem
    fuel_type = Column(String(50))  # Tipo de combustível
    transmission = Column(String(50))  # Câmbio
    color = Column(String(50))  # Cor
    doors = Column(Integer)  # Número de portas
    engine = Column(String(100))  # Motorização

    # Metadados para RAG
    embedding = Column(ARRAY(Float))  # Vetor de embedding para busca semântica
    search_text = Column(Text)  # Texto concatenado para busca

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "name": self.name,
            "code": self.code,
            "category": self.category,
            "brand": self.brand,
            "model": self.model,
            "year": self.year,
            "year_fab": self.year_fab,
            "price": self.price,
            "price_fipe": self.price_fipe,
            "price_promo": self.price_promo,
            "description": self.description,
            "short_description": self.short_description,
            "features": self.features or [],
            "specifications": self.specifications or {},
            "dynamic_fields": self.dynamic_fields or {},
            "main_image": self.main_image,
            "images": self.images or [],
            "video_url": self.video_url,
            "is_available": self.is_available,
            "is_featured": self.is_featured,
            "stock_quantity": self.stock_quantity,
            "location": self.location,
            "mileage": self.mileage,
            "fuel_type": self.fuel_type,
            "transmission": self.transmission,
            "color": self.color,
            "doors": self.doors,
            "engine": self.engine
        }

    def to_search_text(self) -> str:
        """Gera texto para busca e embedding"""
        parts = [
            self.name or "",
            self.brand or "",
            self.model or "",
            f"{self.year}" if self.year else "",
            self.category or "",
            self.color or "",
            self.fuel_type or "",
            self.transmission or "",
            self.description or "",
            self.short_description or "",
            " ".join(self.features or []),
            f"R$ {self.price:,.2f}".replace(",", ".") if self.price else "",
            f"{self.mileage} km" if self.mileage else "",
            self.location or ""
        ]

        # Incluir campos dinamicos do schema
        if self.dynamic_fields:
            for key, value in self.dynamic_fields.items():
                if value:
                    parts.append(str(value))

        return " ".join([p for p in parts if p])

    def to_ai_context(self, schema_fields=None) -> str:
        """Gera contexto formatado para a IA"""
        lines = [f"**{self.name}**"]

        if self.price:
            lines.append(f"Preço: R$ {self.price:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

        # Campos dinamicos com formatacao do schema
        if self.dynamic_fields and schema_fields:
            for field in schema_fields:
                if field.get("show_in_rag", True):
                    value = self.dynamic_fields.get(field["key"])
                    if value:
                        label = field.get("rag_label", field.get("label", field["key"]))
                        fmt = field.get("rag_format")
                        if fmt == "currency":
                            value = f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                        elif fmt == "km":
                            value = f"{int(value):,} km".replace(",", ".")
                        elif fmt == "number":
                            value = f"{int(value):,}".replace(",", ".")
                        lines.append(f"{label}: {value}")
        elif self.dynamic_fields:
            # Sem schema, mostra campos dinamicos genericamente
            for key, value in self.dynamic_fields.items():
                if value:
                    lines.append(f"{key}: {value}")

        # Campos legados (para compatibilidade)
        if self.year:
            lines.append(f"Ano: {self.year_fab or self.year}/{self.year}")

        if self.mileage:
            lines.append(f"Km: {self.mileage:,}".replace(",", "."))

        if self.color:
            lines.append(f"Cor: {self.color}")

        if self.fuel_type:
            lines.append(f"Combustível: {self.fuel_type}")

        if self.transmission:
            lines.append(f"Câmbio: {self.transmission}")

        if self.engine:
            lines.append(f"Motor: {self.engine}")

        if self.short_description:
            lines.append(f"Descrição: {self.short_description}")

        if self.features:
            lines.append(f"Itens: {', '.join(self.features[:5])}")

        if self.is_available:
            lines.append("Status: Disponível")
        else:
            lines.append("Status: Vendido/Indisponível")

        return "\n".join(lines)
