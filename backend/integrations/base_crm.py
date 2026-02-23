"""
Base CRM Interface - Interface abstrata para integracoes CRM
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class CRMProvider(str, Enum):
    """Provedores de CRM suportados"""
    HUBSPOT = "hubspot"
    PIPEDRIVE = "pipedrive"


@dataclass
class CRMContact:
    """Representa um contato no CRM"""
    id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    source: str = "closefy_ai"
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(p for p in parts if p)


@dataclass
class CRMDeal:
    """Representa um negocio/oportunidade no CRM"""
    id: Optional[str] = None
    name: str = ""
    value: float = 0.0
    currency: str = "BRL"
    stage: str = "new"
    contact_id: Optional[str] = None
    pipeline_id: Optional[str] = None
    owner_id: Optional[str] = None
    source: str = "closefy_ai"
    custom_properties: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    expected_close_date: Optional[datetime] = None


@dataclass
class CRMNote:
    """Representa uma nota/atividade no CRM"""
    id: Optional[str] = None
    content: str = ""
    contact_id: Optional[str] = None
    deal_id: Optional[str] = None
    created_at: Optional[datetime] = None


class BaseCRM(ABC):
    """Interface abstrata para integracoes CRM"""

    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self._connected = False

    @property
    @abstractmethod
    def provider(self) -> CRMProvider:
        """Retorna o tipo de provedor CRM"""
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Testa a conexao com o CRM"""
        pass

    @abstractmethod
    async def create_contact(self, contact: CRMContact) -> CRMContact:
        """Cria um novo contato no CRM"""
        pass

    @abstractmethod
    async def update_contact(self, contact_id: str, contact: CRMContact) -> CRMContact:
        """Atualiza um contato existente"""
        pass

    @abstractmethod
    async def find_contact_by_email(self, email: str) -> Optional[CRMContact]:
        """Busca contato por email"""
        pass

    @abstractmethod
    async def find_contact_by_phone(self, phone: str) -> Optional[CRMContact]:
        """Busca contato por telefone"""
        pass

    @abstractmethod
    async def create_deal(self, deal: CRMDeal) -> CRMDeal:
        """Cria um novo negocio/oportunidade"""
        pass

    @abstractmethod
    async def update_deal(self, deal_id: str, deal: CRMDeal) -> CRMDeal:
        """Atualiza um negocio existente"""
        pass

    @abstractmethod
    async def add_note(self, note: CRMNote) -> CRMNote:
        """Adiciona uma nota a um contato ou negocio"""
        pass

    @abstractmethod
    async def get_pipelines(self) -> List[Dict[str, Any]]:
        """Lista pipelines/funis disponiveis"""
        pass

    @abstractmethod
    async def get_stages(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Lista estagios de um pipeline"""
        pass

    async def sync_conversation(
        self,
        phone: str,
        name: Optional[str],
        conversation_summary: str,
        products_discussed: List[str] = None,
        outcome: str = None,
        lead_score: int = None
    ) -> Dict[str, Any]:
        """
        Sincroniza uma conversa do Closefy com o CRM.
        Cria/atualiza contato e adiciona nota com resumo.
        """
        # Buscar ou criar contato
        contact = await self.find_contact_by_phone(phone)

        if not contact:
            # Criar novo contato
            first_name = name.split()[0] if name else None
            last_name = " ".join(name.split()[1:]) if name and len(name.split()) > 1 else None

            contact = CRMContact(
                phone=phone,
                first_name=first_name,
                last_name=last_name,
                source="closefy_ai",
                custom_properties={
                    "lead_score": lead_score,
                    "products_interested": ", ".join(products_discussed or [])
                }
            )
            contact = await self.create_contact(contact)
        else:
            # Atualizar contato existente
            if lead_score:
                contact.custom_properties["lead_score"] = lead_score
            if products_discussed:
                existing = contact.custom_properties.get("products_interested", "")
                new_products = ", ".join(products_discussed)
                contact.custom_properties["products_interested"] = f"{existing}, {new_products}".strip(", ")

            contact = await self.update_contact(contact.id, contact)

        # Adicionar nota com resumo da conversa
        note = CRMNote(
            content=f"[Closefy AI] {conversation_summary}",
            contact_id=contact.id
        )
        await self.add_note(note)

        return {
            "contact_id": contact.id,
            "contact_created": contact.created_at == contact.updated_at,
            "note_added": True
        }
