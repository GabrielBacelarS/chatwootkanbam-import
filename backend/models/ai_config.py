from sqlalchemy import Column, String, Boolean, Integer, Text, Time, ARRAY, DateTime, ForeignKey, func, Float
from datetime import time
from backend.core.database import Base


class AIConfig(Base):
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), unique=True)
    enabled = Column(Boolean, default=False)
    provider = Column(String(50), default="openai")
    api_key = Column(String(500))
    openai_key_for_whisper = Column(String(500))
    model = Column(String(100), default="gpt-4o-mini")
    system_prompt = Column(Text)
    welcome_message = Column(Text)
    transfer_keywords = Column(ARRAY(String), default=["atendente", "humano", "pessoa", "falar com alguém"])
    max_messages_before_transfer = Column(Integer, default=10)
    only_unassigned = Column(Boolean, default=True)
    split_message_at = Column(Integer, default=1000)
    split_by_paragraph = Column(Boolean, default=True)

    # Modo de quebra de mensagens:
    # - "none": Sem quebra (mensagem unica)
    # - "paragraph": Por paragrafos
    # - "sentence": Por sentencas (pontos finais)
    # - "character": Apenas por limite de caracteres
    # - "smart": Inteligente (paragrafos > sentencas > palavras)
    split_mode = Column(String(20), default="smart")
    working_hours_start = Column(Time, default=time(8, 0))
    working_hours_end = Column(Time, default=time(18, 0))
    working_days = Column(ARRAY(Integer), default=[1, 2, 3, 4, 5])

    # Novo: IA só responde quando atribuída a um agente específico (nome)
    required_assignee_name = Column(String(100), nullable=True)  # Ex: "IA"

    # Novo: ID da equipe para transferir quando detectar palavra-chave
    transfer_team_id = Column(Integer, nullable=True)

    # Modo Agente LangChain (com tools: buscar produtos, calcular financiamento, etc)
    use_agent_mode = Column(Boolean, default=True)

    # Tools habilitadas para o agente (lista de nomes: buscar_produtos, calcular_financiamento, enviar_imagem, agendar_visita)
    enabled_tools = Column(ARRAY(String), default=["buscar_produtos", "calcular_financiamento", "enviar_imagem", "agendar_visita"])

    # Keywords que forcam uso de tools (configuravel por tipo de negocio)
    # Ex para veiculos: ["carro", "carros", "veiculo", "preco", "estoque"]
    # Ex para ar condicionado: ["ar", "condicionado", "split", "btu", "instalacao"]
    # Ex para roupas: ["roupa", "camisa", "calcado", "tamanho", "cor"]
    product_keywords = Column(ARRAY(String), default=[
        "produto", "produtos", "estoque", "disponivel", "disponiveis",
        "tem", "temos", "quais", "preco", "precos", "quanto", "valor",
        "valores", "opcao", "opcoes", "ver", "mostrar", "conhecer", "saber"
    ])

    # Modo de deteccao de intencao:
    # - "keywords": Usa palavras-chave fixas (comportamento antigo)
    # - "auto": IA identifica automaticamente quando buscar produtos (inteligente)
    # - "always": Sempre busca produtos em qualquer mensagem
    intent_detection_mode = Column(String(20), default="keywords")

    # Tempo de espera para agrupar mensagens (debounce) em segundos
    # Permite que usuario envie varias mensagens seguidas antes da IA responder
    debounce_seconds = Column(Float, default=10.0)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "enabled": self.enabled,
            "provider": self.provider,
            "api_key": self.api_key,
            "openai_key_for_whisper": self.openai_key_for_whisper,
            "model": self.model,
            "system_prompt": self.system_prompt,
            "welcome_message": self.welcome_message,
            "transfer_keywords": self.transfer_keywords or [],
            "max_messages_before_transfer": self.max_messages_before_transfer,
            "only_unassigned": self.only_unassigned,
            "split_message_at": self.split_message_at,
            "split_by_paragraph": self.split_by_paragraph,
            "split_mode": self.split_mode or "smart",
            "working_hours_start": str(self.working_hours_start) if self.working_hours_start else None,
            "working_hours_end": str(self.working_hours_end) if self.working_hours_end else None,
            "working_days": self.working_days or [],
            "required_assignee_name": self.required_assignee_name,
            "transfer_team_id": self.transfer_team_id,
            "use_agent_mode": self.use_agent_mode if self.use_agent_mode is not None else True,
            "enabled_tools": self.enabled_tools or ["buscar_produtos", "calcular_financiamento", "enviar_imagem", "agendar_visita"],
            "product_keywords": self.product_keywords or [
                "produto", "produtos", "estoque", "disponivel", "disponiveis",
                "tem", "temos", "quais", "preco", "precos", "quanto", "valor",
                "valores", "opcao", "opcoes", "ver", "mostrar", "conhecer", "saber"
            ],
            "debounce_seconds": self.debounce_seconds if self.debounce_seconds is not None else 10.0,
            "intent_detection_mode": self.intent_detection_mode or "keywords"
        }
