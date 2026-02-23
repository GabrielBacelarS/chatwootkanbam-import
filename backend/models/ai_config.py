from sqlalchemy import Column, String, Boolean, Integer, Text, Time, ARRAY, DateTime, ForeignKey, func, Float
from datetime import time
from backend.core.database import Base


class AIConfig(Base):
    """
    Configuracao de IA por cliente

    IMPORTANTE: Os campos api_key e openai_key_for_whisper sao armazenados encriptados.
    Use os metodos get_api_key() e set_api_key() para acessar/modificar.
    """
    __tablename__ = "ai_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), unique=True)
    enabled = Column(Boolean, default=False)
    provider = Column(String(50), default="openai")

    # API Keys armazenadas encriptadas
    _api_key = Column("api_key", String(500))
    _openai_key_for_whisper = Column("openai_key_for_whisper", String(500))
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

    # Properties para encriptacao automatica de API keys
    @property
    def api_key(self) -> str:
        """Retorna API key decriptada"""
        if not self._api_key:
            return None
        from backend.core.encryption import decrypt
        return decrypt(self._api_key)

    @api_key.setter
    def api_key(self, value: str):
        """Armazena API key encriptada"""
        if not value:
            self._api_key = None
            return
        from backend.core.encryption import encrypt_if_needed
        self._api_key = encrypt_if_needed(value)

    @property
    def openai_key_for_whisper(self) -> str:
        """Retorna OpenAI key para Whisper decriptada"""
        if not self._openai_key_for_whisper:
            return None
        from backend.core.encryption import decrypt
        return decrypt(self._openai_key_for_whisper)

    @openai_key_for_whisper.setter
    def openai_key_for_whisper(self, value: str):
        """Armazena OpenAI key para Whisper encriptada"""
        if not value:
            self._openai_key_for_whisper = None
            return
        from backend.core.encryption import encrypt_if_needed
        self._openai_key_for_whisper = encrypt_if_needed(value)

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
