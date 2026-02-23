"""
HubSpot CRM Integration
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from backend.integrations.base_crm import (
    BaseCRM, CRMProvider, CRMContact, CRMDeal, CRMNote
)

logger = logging.getLogger(__name__)


class HubSpotCRM(BaseCRM):
    """Integracao com HubSpot CRM"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        self._client = None

    @property
    def provider(self) -> CRMProvider:
        return CRMProvider.HUBSPOT

    def _get_client(self):
        """Inicializa cliente HubSpot lazily"""
        if not self._client:
            try:
                from hubspot import HubSpot
                self._client = HubSpot(access_token=self.api_key)
            except ImportError:
                raise ImportError("hubspot-api-client nao esta instalado. Execute: pip install hubspot-api-client")
        return self._client

    async def test_connection(self) -> bool:
        """Testa a conexao com HubSpot"""
        try:
            client = self._get_client()
            # Tenta buscar info da conta
            response = client.crm.contacts.basic_api.get_page(limit=1)
            self._connected = True
            logger.info("HubSpot: Conexao bem sucedida")
            return True
        except Exception as e:
            logger.error(f"HubSpot: Erro de conexao - {e}")
            self._connected = False
            return False

    async def create_contact(self, contact: CRMContact) -> CRMContact:
        """Cria contato no HubSpot"""
        try:
            client = self._get_client()

            properties = {
                "firstname": contact.first_name or "",
                "lastname": contact.last_name or "",
                "phone": contact.phone or "",
                "email": contact.email or "",
                "company": contact.company or "",
                "hs_lead_status": "NEW",
                "lifecyclestage": "lead"
            }

            # Adicionar propriedades customizadas
            for key, value in contact.custom_properties.items():
                if value is not None:
                    properties[key] = str(value)

            from hubspot.crm.contacts import SimplePublicObjectInputForCreate
            simple_public_object_input = SimplePublicObjectInputForCreate(
                properties=properties
            )

            response = client.crm.contacts.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )

            contact.id = response.id
            contact.created_at = datetime.utcnow()
            contact.updated_at = datetime.utcnow()

            logger.info(f"HubSpot: Contato criado - ID {contact.id}")
            return contact

        except Exception as e:
            logger.error(f"HubSpot: Erro ao criar contato - {e}")
            raise

    async def update_contact(self, contact_id: str, contact: CRMContact) -> CRMContact:
        """Atualiza contato no HubSpot"""
        try:
            client = self._get_client()

            properties = {}
            if contact.first_name:
                properties["firstname"] = contact.first_name
            if contact.last_name:
                properties["lastname"] = contact.last_name
            if contact.phone:
                properties["phone"] = contact.phone
            if contact.email:
                properties["email"] = contact.email
            if contact.company:
                properties["company"] = contact.company

            # Adicionar propriedades customizadas
            for key, value in contact.custom_properties.items():
                if value is not None:
                    properties[key] = str(value)

            from hubspot.crm.contacts import SimplePublicObjectInput
            simple_public_object_input = SimplePublicObjectInput(
                properties=properties
            )

            response = client.crm.contacts.basic_api.update(
                contact_id=contact_id,
                simple_public_object_input=simple_public_object_input
            )

            contact.id = response.id
            contact.updated_at = datetime.utcnow()

            logger.info(f"HubSpot: Contato atualizado - ID {contact_id}")
            return contact

        except Exception as e:
            logger.error(f"HubSpot: Erro ao atualizar contato - {e}")
            raise

    async def find_contact_by_email(self, email: str) -> Optional[CRMContact]:
        """Busca contato por email no HubSpot"""
        try:
            client = self._get_client()

            from hubspot.crm.contacts import PublicObjectSearchRequest

            search_request = PublicObjectSearchRequest(
                filter_groups=[{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }],
                properties=["firstname", "lastname", "email", "phone", "company"]
            )

            response = client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )

            if response.results:
                result = response.results[0]
                props = result.properties or {}
                return CRMContact(
                    id=result.id,
                    first_name=props.get("firstname"),
                    last_name=props.get("lastname"),
                    email=props.get("email"),
                    phone=props.get("phone"),
                    company=props.get("company"),
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )

            return None

        except Exception as e:
            logger.error(f"HubSpot: Erro ao buscar contato por email - {e}")
            return None

    async def find_contact_by_phone(self, phone: str) -> Optional[CRMContact]:
        """Busca contato por telefone no HubSpot"""
        try:
            client = self._get_client()

            # Normalizar telefone (remover caracteres especiais)
            normalized_phone = "".join(c for c in phone if c.isdigit())

            from hubspot.crm.contacts import PublicObjectSearchRequest

            search_request = PublicObjectSearchRequest(
                filter_groups=[{
                    "filters": [{
                        "propertyName": "phone",
                        "operator": "CONTAINS_TOKEN",
                        "value": normalized_phone[-9:]  # Ultimos 9 digitos
                    }]
                }],
                properties=["firstname", "lastname", "email", "phone", "company"]
            )

            response = client.crm.contacts.search_api.do_search(
                public_object_search_request=search_request
            )

            if response.results:
                result = response.results[0]
                props = result.properties or {}
                return CRMContact(
                    id=result.id,
                    first_name=props.get("firstname"),
                    last_name=props.get("lastname"),
                    email=props.get("email"),
                    phone=props.get("phone"),
                    company=props.get("company"),
                    created_at=result.created_at,
                    updated_at=result.updated_at
                )

            return None

        except Exception as e:
            logger.error(f"HubSpot: Erro ao buscar contato por telefone - {e}")
            return None

    async def create_deal(self, deal: CRMDeal) -> CRMDeal:
        """Cria negocio no HubSpot"""
        try:
            client = self._get_client()

            properties = {
                "dealname": deal.name or "Negocio Closefy AI",
                "amount": str(deal.value) if deal.value else "0",
                "dealstage": deal.stage or "appointmentscheduled",
                "pipeline": deal.pipeline_id or "default"
            }

            if deal.expected_close_date:
                properties["closedate"] = deal.expected_close_date.strftime("%Y-%m-%d")

            # Adicionar propriedades customizadas
            for key, value in deal.custom_properties.items():
                if value is not None:
                    properties[key] = str(value)

            from hubspot.crm.deals import SimplePublicObjectInputForCreate

            simple_public_object_input = SimplePublicObjectInputForCreate(
                properties=properties
            )

            response = client.crm.deals.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )

            deal.id = response.id
            deal.created_at = datetime.utcnow()
            deal.updated_at = datetime.utcnow()

            # Associar ao contato se houver
            if deal.contact_id:
                try:
                    from hubspot.crm.deals import BatchInputPublicAssociation
                    from hubspot.crm.associations import AssociationSpec

                    client.crm.deals.associations_api.create(
                        deal_id=deal.id,
                        to_object_type="contacts",
                        to_object_id=deal.contact_id,
                        association_spec=[
                            AssociationSpec(
                                association_category="HUBSPOT_DEFINED",
                                association_type_id=3  # Deal to Contact
                            )
                        ]
                    )
                except Exception as assoc_error:
                    logger.warning(f"HubSpot: Erro ao associar deal ao contato - {assoc_error}")

            logger.info(f"HubSpot: Deal criado - ID {deal.id}")
            return deal

        except Exception as e:
            logger.error(f"HubSpot: Erro ao criar deal - {e}")
            raise

    async def update_deal(self, deal_id: str, deal: CRMDeal) -> CRMDeal:
        """Atualiza negocio no HubSpot"""
        try:
            client = self._get_client()

            properties = {}
            if deal.name:
                properties["dealname"] = deal.name
            if deal.value:
                properties["amount"] = str(deal.value)
            if deal.stage:
                properties["dealstage"] = deal.stage

            # Adicionar propriedades customizadas
            for key, value in deal.custom_properties.items():
                if value is not None:
                    properties[key] = str(value)

            from hubspot.crm.deals import SimplePublicObjectInput

            simple_public_object_input = SimplePublicObjectInput(
                properties=properties
            )

            response = client.crm.deals.basic_api.update(
                deal_id=deal_id,
                simple_public_object_input=simple_public_object_input
            )

            deal.id = response.id
            deal.updated_at = datetime.utcnow()

            logger.info(f"HubSpot: Deal atualizado - ID {deal_id}")
            return deal

        except Exception as e:
            logger.error(f"HubSpot: Erro ao atualizar deal - {e}")
            raise

    async def add_note(self, note: CRMNote) -> CRMNote:
        """Adiciona nota no HubSpot (como engagement/note)"""
        try:
            client = self._get_client()

            from hubspot.crm.objects.notes import SimplePublicObjectInputForCreate

            properties = {
                "hs_note_body": note.content,
                "hs_timestamp": str(int(datetime.utcnow().timestamp() * 1000))
            }

            simple_public_object_input = SimplePublicObjectInputForCreate(
                properties=properties
            )

            response = client.crm.objects.notes.basic_api.create(
                simple_public_object_input_for_create=simple_public_object_input
            )

            note.id = response.id
            note.created_at = datetime.utcnow()

            # Associar ao contato se houver
            if note.contact_id:
                try:
                    from hubspot.crm.associations import AssociationSpec

                    client.crm.objects.notes.associations_api.create(
                        note_id=note.id,
                        to_object_type="contacts",
                        to_object_id=note.contact_id,
                        association_spec=[
                            AssociationSpec(
                                association_category="HUBSPOT_DEFINED",
                                association_type_id=202  # Note to Contact
                            )
                        ]
                    )
                except Exception as assoc_error:
                    logger.warning(f"HubSpot: Erro ao associar nota ao contato - {assoc_error}")

            # Associar ao deal se houver
            if note.deal_id:
                try:
                    from hubspot.crm.associations import AssociationSpec

                    client.crm.objects.notes.associations_api.create(
                        note_id=note.id,
                        to_object_type="deals",
                        to_object_id=note.deal_id,
                        association_spec=[
                            AssociationSpec(
                                association_category="HUBSPOT_DEFINED",
                                association_type_id=214  # Note to Deal
                            )
                        ]
                    )
                except Exception as assoc_error:
                    logger.warning(f"HubSpot: Erro ao associar nota ao deal - {assoc_error}")

            logger.info(f"HubSpot: Nota criada - ID {note.id}")
            return note

        except Exception as e:
            logger.error(f"HubSpot: Erro ao criar nota - {e}")
            raise

    async def get_pipelines(self) -> List[Dict[str, Any]]:
        """Lista pipelines de deals no HubSpot"""
        try:
            client = self._get_client()

            response = client.crm.pipelines.pipelines_api.get_all(
                object_type="deals"
            )

            pipelines = []
            for pipeline in response.results:
                pipelines.append({
                    "id": pipeline.id,
                    "label": pipeline.label,
                    "display_order": pipeline.display_order,
                    "stages": [
                        {
                            "id": stage.id,
                            "label": stage.label,
                            "display_order": stage.display_order
                        }
                        for stage in pipeline.stages
                    ]
                })

            return pipelines

        except Exception as e:
            logger.error(f"HubSpot: Erro ao buscar pipelines - {e}")
            return []

    async def get_stages(self, pipeline_id: str) -> List[Dict[str, Any]]:
        """Lista estagios de um pipeline"""
        try:
            pipelines = await self.get_pipelines()

            for pipeline in pipelines:
                if pipeline["id"] == pipeline_id:
                    return pipeline.get("stages", [])

            return []

        except Exception as e:
            logger.error(f"HubSpot: Erro ao buscar stages - {e}")
            return []
