"""
Pipedrive CRM Integration
"""
import logging
import httpx
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.integrations.base_crm import (
    BaseCRM, CRMProvider, CRMContact, CRMDeal, CRMNote
)

logger = logging.getLogger(__name__)


class PipedriveCRM(BaseCRM):
    """Integracao com Pipedrive CRM"""

    BASE_URL = "https://api.pipedrive.com/v1"

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self._client = None

    @property
    def provider(self) -> CRMProvider:
        return CRMProvider.PIPEDRIVE

    def _get_client(self) -> httpx.AsyncClient:
        """Retorna cliente HTTP configurado"""
        if not self._client:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                params={"api_token": self.api_key},
                timeout=30.0
            )
        return self._client

    async def test_connection(self) -> bool:
        """Testa a conexao com Pipedrive"""
        try:
            client = self._get_client()
            response = await client.get("/users/me")

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    self._connected = True
                    logger.info("Pipedrive: Conexao bem sucedida")
                    return True

            self._connected = False
            logger.error(f"Pipedrive: Erro de conexao - Status {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Pipedrive: Erro de conexao - {e}")
            self._connected = False
            return False

    async def create_contact(self, contact: CRMContact) -> CRMContact:
        """Cria pessoa no Pipedrive"""
        try:
            client = self._get_client()

            data = {
                "name": contact.full_name or "Contato Closefy"
            }

            if contact.email:
                data["email"] = [{"value": contact.email, "primary": True}]

            if contact.phone:
                data["phone"] = [{"value": contact.phone, "primary": True}]

            # Adicionar campos customizados
            for key, value in contact.custom_properties.items():
                if value is not None:
                    data[key] = value

            response = await client.post("/persons", json=data)
            result = response.json()

            if result.get("success"):
                person = result["data"]
                contact.id = str(person["id"])
                contact.created_at = datetime.utcnow()
                contact.updated_at = datetime.utcnow()

                logger.info(f"Pipedrive: Pessoa criada - ID {contact.id}")
                return contact
            else:
                raise Exception(result.get("error", "Erro desconhecido"))

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao criar pessoa - {e}")
            raise

    async def update_contact(self, contact_id: str, contact: CRMContact) -> CRMContact:
        """Atualiza pessoa no Pipedrive"""
        try:
            client = self._get_client()

            data = {}

            if contact.full_name:
                data["name"] = contact.full_name

            if contact.email:
                data["email"] = [{"value": contact.email, "primary": True}]

            if contact.phone:
                data["phone"] = [{"value": contact.phone, "primary": True}]

            # Adicionar campos customizados
            for key, value in contact.custom_properties.items():
                if value is not None:
                    data[key] = value

            response = await client.put(f"/persons/{contact_id}", json=data)
            result = response.json()

            if result.get("success"):
                contact.id = contact_id
                contact.updated_at = datetime.utcnow()

                logger.info(f"Pipedrive: Pessoa atualizada - ID {contact_id}")
                return contact
            else:
                raise Exception(result.get("error", "Erro desconhecido"))

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao atualizar pessoa - {e}")
            raise

    async def find_contact_by_email(self, email: str) -> Optional[CRMContact]:
        """Busca pessoa por email no Pipedrive"""
        try:
            client = self._get_client()

            response = await client.get(
                "/persons/search",
                params={"term": email, "fields": "email"}
            )
            result = response.json()

            if result.get("success") and result.get("data", {}).get("items"):
                item = result["data"]["items"][0]
                person = item.get("item", {})

                return CRMContact(
                    id=str(person.get("id")),
                    first_name=person.get("name", "").split()[0] if person.get("name") else None,
                    last_name=" ".join(person.get("name", "").split()[1:]) if person.get("name") else None,
                    email=email,
                    phone=None  # Pipedrive nao retorna phone na busca
                )

            return None

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao buscar pessoa por email - {e}")
            return None

    async def find_contact_by_phone(self, phone: str) -> Optional[CRMContact]:
        """Busca pessoa por telefone no Pipedrive"""
        try:
            client = self._get_client()

            # Normalizar telefone
            normalized_phone = "".join(c for c in phone if c.isdigit())

            response = await client.get(
                "/persons/search",
                params={"term": normalized_phone[-9:], "fields": "phone"}
            )
            result = response.json()

            if result.get("success") and result.get("data", {}).get("items"):
                item = result["data"]["items"][0]
                person = item.get("item", {})

                return CRMContact(
                    id=str(person.get("id")),
                    first_name=person.get("name", "").split()[0] if person.get("name") else None,
                    last_name=" ".join(person.get("name", "").split()[1:]) if person.get("name") else None,
                    phone=phone
                )

            return None

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao buscar pessoa por telefone - {e}")
            return None

    async def create_deal(self, deal: CRMDeal) -> CRMDeal:
        """Cria negocio no Pipedrive"""
        try:
            client = self._get_client()

            data = {
                "title": deal.name or "Negocio Closefy AI",
                "value": deal.value or 0,
                "currency": deal.currency or "BRL"
            }

            if deal.contact_id:
                data["person_id"] = int(deal.contact_id)

            if deal.pipeline_id:
                data["pipeline_id"] = int(deal.pipeline_id)

            if deal.stage:
                data["stage_id"] = int(deal.stage)

            if deal.owner_id:
                data["user_id"] = int(deal.owner_id)

            if deal.expected_close_date:
                data["expected_close_date"] = deal.expected_close_date.strftime("%Y-%m-%d")

            # Adicionar campos customizados
            for key, value in deal.custom_properties.items():
                if value is not None:
                    data[key] = value

            response = await client.post("/deals", json=data)
            result = response.json()

            if result.get("success"):
                deal_data = result["data"]
                deal.id = str(deal_data["id"])
                deal.created_at = datetime.utcnow()
                deal.updated_at = datetime.utcnow()

                logger.info(f"Pipedrive: Deal criado - ID {deal.id}")
                return deal
            else:
                raise Exception(result.get("error", "Erro desconhecido"))

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao criar deal - {e}")
            raise

    async def update_deal(self, deal_id: str, deal: CRMDeal) -> CRMDeal:
        """Atualiza negocio no Pipedrive"""
        try:
            client = self._get_client()

            data = {}

            if deal.name:
                data["title"] = deal.name

            if deal.value is not None:
                data["value"] = deal.value

            if deal.stage:
                data["stage_id"] = int(deal.stage)

            # Adicionar campos customizados
            for key, value in deal.custom_properties.items():
                if value is not None:
                    data[key] = value

            response = await client.put(f"/deals/{deal_id}", json=data)
            result = response.json()

            if result.get("success"):
                deal.id = deal_id
                deal.updated_at = datetime.utcnow()

                logger.info(f"Pipedrive: Deal atualizado - ID {deal_id}")
                return deal
            else:
                raise Exception(result.get("error", "Erro desconhecido"))

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao atualizar deal - {e}")
            raise

    async def add_note(self, note: CRMNote) -> CRMNote:
        """Adiciona nota no Pipedrive"""
        try:
            client = self._get_client()

            data = {
                "content": note.content
            }

            if note.contact_id:
                data["person_id"] = int(note.contact_id)

            if note.deal_id:
                data["deal_id"] = int(note.deal_id)

            response = await client.post("/notes", json=data)
            result = response.json()

            if result.get("success"):
                note_data = result["data"]
                note.id = str(note_data["id"])
                note.created_at = datetime.utcnow()

                logger.info(f"Pipedrive: Nota criada - ID {note.id}")
                return note
            else:
                raise Exception(result.get("error", "Erro desconhecido"))

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao criar nota - {e}")
            raise

    async def get_pipelines(self) -> List[Dict[str, Any]]:
        """Lista pipelines no Pipedrive"""
        try:
            client = self._get_client()

            response = await client.get("/pipelines")
            result = response.json()

            if result.get("success"):
                pipelines = []
                for pipeline in result.get("data", []):
                    pipelines.append({
                        "id": str(pipeline["id"]),
                        "label": pipeline["name"],
                        "display_order": pipeline.get("order_nr", 0),
                        "stages": []  # Stages sao buscadas separadamente
                    })
                return pipelines

            return []

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao buscar pipelines - {e}")
            return []

    async def get_stages(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Lista estagios de um pipeline no Pipedrive"""
        try:
            client = self._get_client()

            response = await client.get(
                "/stages",
                params={"pipeline_id": pipeline_id}
            )
            result = response.json()

            if result.get("success"):
                stages = []
                for stage in result.get("data", []):
                    stages.append({
                        "id": str(stage["id"]),
                        "label": stage["name"],
                        "display_order": stage.get("order_nr", 0)
                    })
                return stages

            return []

        except Exception as e:
            logger.error(f"Pipedrive: Erro ao buscar stages - {e}")
            return []

    async def close(self):
        """Fecha o cliente HTTP"""
        if self._client:
            await self._client.aclose()
            self._client = None
