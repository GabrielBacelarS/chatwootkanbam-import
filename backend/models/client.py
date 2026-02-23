from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func
from backend.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    slug = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    api_url = Column(String(500), nullable=False)  # URL do Chatwoot
    api_token = Column(String(500), nullable=False)
    account_id = Column(String(50), nullable=False)

    # Schema de produto usado por este cliente
    product_schema_id = Column(Integer, ForeignKey("product_schemas.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def chatwoot_url(self):
        """Alias para compatibilidade"""
        return self.api_url

    def to_dict(self):
        return {
            "slug": self.slug,
            "name": self.name,
            "chatwoot_url": self.api_url,  # Retorna como chatwoot_url para API
            "api_token": self.api_token,
            "account_id": self.account_id,
            "product_schema_id": self.product_schema_id
        }
