"""
Modelo de Configuracao CRM por Cliente
"""
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from backend.core.database import Base
from backend.core.encryption import encrypt_if_needed, decrypt


class CRMConfig(Base):
    """Configuracao de integracao CRM por cliente"""
    __tablename__ = "crm_configs"

    id = Column(Integer, primary_key=True, index=True)
    client_slug = Column(String(100), ForeignKey("clients.slug", ondelete="CASCADE"), unique=True, index=True)

    # Provedor e credenciais
    provider = Column(String(50))  # hubspot, pipedrive
    _api_key = Column("api_key", Text)  # Encriptado

    # Status
    enabled = Column(Boolean, default=False)
    connected = Column(Boolean, default=False)
    last_sync_at = Column(DateTime(timezone=True))
    last_error = Column(Text)

    # Configuracoes de sincronizacao
    auto_create_contacts = Column(Boolean, default=True)  # Criar contatos automaticamente
    auto_create_deals = Column(Boolean, default=False)  # Criar deals automaticamente
    sync_notes = Column(Boolean, default=True)  # Sincronizar notas/resumos
    sync_on_transfer = Column(Boolean, default=True)  # Sincronizar ao transferir para humano

    # Mapeamento de pipeline/stages
    default_pipeline_id = Column(String(100))
    default_stage_id = Column(String(100))
    converted_stage_id = Column(String(100))

    # Campos customizados para mapear
    field_mapping = Column(JSONB, default={})
    # Ex: {"lead_score": "closefy_lead_score", "products_interested": "closefy_products"}

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def api_key(self) -> str:
        """Retorna API key decriptada"""
        if not self._api_key:
            return None
        return decrypt(self._api_key)

    @api_key.setter
    def api_key(self, value: str):
        """Armazena API key encriptada"""
        if not value:
            self._api_key = None
            return
        self._api_key = encrypt_if_needed(value)

    def to_dict(self) -> dict:
        """Converte para dicionario (sem expor API key completa)"""
        return {
            "id": self.id,
            "client_slug": self.client_slug,
            "provider": self.provider,
            "api_key_set": bool(self._api_key),
            "enabled": self.enabled,
            "connected": self.connected,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_error": self.last_error,
            "auto_create_contacts": self.auto_create_contacts,
            "auto_create_deals": self.auto_create_deals,
            "sync_notes": self.sync_notes,
            "sync_on_transfer": self.sync_on_transfer,
            "default_pipeline_id": self.default_pipeline_id,
            "default_stage_id": self.default_stage_id,
            "converted_stage_id": self.converted_stage_id,
            "field_mapping": self.field_mapping or {}
        }
