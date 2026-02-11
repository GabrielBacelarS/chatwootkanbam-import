from sqlalchemy import Column, String, DateTime, func
from app.core.database import Base


class Client(Base):
    __tablename__ = "clients"

    slug = Column(String(100), primary_key=True)
    name = Column(String(255), nullable=False)
    api_url = Column(String(500), nullable=False)  # URL do Chatwoot
    api_token = Column(String(500), nullable=False)
    account_id = Column(String(50), nullable=False)
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
            "account_id": self.account_id
        }
