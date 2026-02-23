from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from backend.core.database import Base


class Client(Base):
    """
    Cliente/Workspace do sistema

    IMPORTANTE: O campo api_token e armazenado encriptado.
    Use a property api_token para acessar/modificar.
    """
    __tablename__ = "clients"

    slug = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    api_url = Column(String(500), nullable=False)  # URL do Chatwoot
    _api_token = Column("api_token", String(500), nullable=False)  # Armazenado encriptado
    account_id = Column(String(50), nullable=False)

    # Schema de produto usado por este cliente
    product_schema_id = Column(Integer, ForeignKey("product_schemas.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def chatwoot_url(self):
        """Alias para compatibilidade"""
        return self.api_url

    @property
    def api_token(self) -> str:
        """Retorna API token decriptado"""
        if not self._api_token:
            return None
        from backend.core.encryption import decrypt
        return decrypt(self._api_token)

    @api_token.setter
    def api_token(self, value: str):
        """Armazena API token encriptado"""
        if not value:
            self._api_token = None
            return
        from backend.core.encryption import encrypt_if_needed
        self._api_token = encrypt_if_needed(value)

    def to_dict(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "chatwoot_url": self.api_url,  # Retorna como chatwoot_url para API
            "api_token": self.api_token,  # Retorna decriptado via property
            "account_id": self.account_id,
            "product_schema_id": self.product_schema_id
        }
