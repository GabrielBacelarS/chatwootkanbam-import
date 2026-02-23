from sqlalchemy import Column, String, Integer, Boolean, Text, DateTime, ForeignKey, func, Float
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from backend.core.database import Base


class AITestCase(Base):
    """Caso de teste para validacao de agentes IA"""
    __tablename__ = "ai_test_cases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"))

    # Identificacao
    name = Column(String(200), nullable=False)
    description = Column(Text)
    category = Column(String(50))  # product_search, financing, scheduling, media

    # Input do teste
    input_message = Column(Text, nullable=False)

    # Criterios de avaliacao
    expected_tools = Column(ARRAY(String), default=[])  # ["buscar_produtos"]
    expected_keywords = Column(ARRAY(String), default=[])  # ["preto", "disponivel"]
    should_not_contain = Column(ARRAY(String), default=[])  # ["erro", "desculpe"]
    expected_tool_args = Column(JSONB)  # {"buscar_produtos": {"query": "preto"}}

    # Pesos para pontuacao (0-10 cada)
    weight_tools = Column(Integer, default=10)
    weight_keywords = Column(Integer, default=10)
    weight_no_errors = Column(Integer, default=10)
    weight_quality = Column(Integer, default=5)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "input_message": self.input_message,
            "expected_tools": self.expected_tools or [],
            "expected_keywords": self.expected_keywords or [],
            "should_not_contain": self.should_not_contain or [],
            "expected_tool_args": self.expected_tool_args,
            "weight_tools": self.weight_tools,
            "weight_keywords": self.weight_keywords,
            "weight_no_errors": self.weight_no_errors,
            "weight_quality": self.weight_quality,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# Templates padrao para diferentes tipos de negocio
DEFAULT_TEST_TEMPLATES = [
    {
        "name": "Busca de produtos generica",
        "category": "product_search",
        "input_message": "Quais produtos voces tem disponiveis?",
        "expected_tools": ["buscar_produtos"],
        "expected_keywords": ["disponivel", "estoque", "produto"],
        "should_not_contain": ["erro", "nao encontrei", "desculpe"],
        "description": "Verifica se o agente busca produtos quando perguntado sobre estoque"
    },
    {
        "name": "Busca por caracteristica",
        "category": "product_search",
        "input_message": "Tem algum produto preto?",
        "expected_tools": ["buscar_produtos"],
        "expected_keywords": ["preto"],
        "should_not_contain": ["nao temos", "indisponivel"],
        "description": "Verifica se o agente filtra por caracteristicas"
    },
    {
        "name": "Busca por preco",
        "category": "product_search",
        "input_message": "Tem algum produto ate 50 mil?",
        "expected_tools": ["buscar_produtos"],
        "expected_keywords": ["preco", "valor", "50"],
        "should_not_contain": [],
        "description": "Verifica se o agente entende filtro por preco"
    },
    {
        "name": "Simulacao de financiamento",
        "category": "financing",
        "input_message": "Quanto fica a parcela de um produto de 80 mil?",
        "expected_tools": ["calcular_financiamento"],
        "expected_keywords": ["parcela", "financiamento", "entrada"],
        "should_not_contain": ["erro", "nao consigo"],
        "description": "Verifica se o agente calcula financiamento corretamente"
    },
    {
        "name": "Agendamento de visita",
        "category": "scheduling",
        "input_message": "Posso agendar uma visita para sabado?",
        "expected_tools": ["agendar_visita"],
        "expected_keywords": ["agend", "visita", "sabado"],
        "should_not_contain": ["nao podemos", "impossivel"],
        "description": "Verifica se o agente agenda visitas"
    },
    {
        "name": "Solicitacao de foto",
        "category": "media",
        "input_message": "Pode me enviar a foto desse produto?",
        "expected_tools": ["enviar_imagem"],
        "expected_keywords": ["foto", "imagem"],
        "should_not_contain": ["nao tenho", "sem foto"],
        "description": "Verifica se o agente envia imagens quando solicitado"
    },
    {
        "name": "Saudacao inicial",
        "category": "greeting",
        "input_message": "Ola, boa tarde!",
        "expected_tools": [],
        "expected_keywords": ["ola", "ajudar", "bem-vindo"],
        "should_not_contain": ["erro"],
        "description": "Verifica se o agente responde saudacoes adequadamente"
    },
    {
        "name": "Pergunta fora do escopo",
        "category": "out_of_scope",
        "input_message": "Qual a previsao do tempo para amanha?",
        "expected_tools": [],
        "expected_keywords": [],
        "should_not_contain": ["aqui esta a previsao", "vai chover"],
        "description": "Verifica se o agente nao responde perguntas fora do escopo"
    }
]
