import httpx
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class ChatwootService:
    """Service para interação com a API do Chatwoot"""

    def __init__(self, base_url: str, api_token: str, account_id: str):
        self.base_url = base_url.rstrip("/")
        self.api_token = api_token
        self.account_id = account_id
        self.headers = {
            "api_access_token": api_token,
            "Content-Type": "application/json"
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1/accounts/{self.account_id}{path}"

    async def _request(
        self,
        method: str,
        path: str,
        json: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Faz requisição para a API do Chatwoot"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=self._url(path),
                headers=self.headers,
                json=json,
                params=params
            )
            response.raise_for_status()
            return response.json() if response.content else {}

    # ===== Conversations =====

    async def get_conversations(
        self,
        status: str = "open",
        assignee_type: str = "all",
        page: int = 1,
        inbox_id: Optional[int] = None,
        labels: Optional[List[str]] = None
    ) -> Dict:
        """Lista conversas"""
        params = {
            "status": status,
            "assignee_type": assignee_type,
            "page": page
        }
        if inbox_id:
            params["inbox_id"] = inbox_id
        if labels:
            params["labels"] = labels

        return await self._request("GET", "/conversations", params=params)

    async def get_conversation(self, conversation_id: int) -> Dict:
        """Obtém detalhes de uma conversa"""
        return await self._request("GET", f"/conversations/{conversation_id}")

    async def get_conversation_messages(self, conversation_id: int) -> Dict:
        """Obtém mensagens de uma conversa"""
        return await self._request("GET", f"/conversations/{conversation_id}/messages")

    async def send_message(
        self,
        conversation_id: int,
        content: str,
        message_type: str = "outgoing",
        private: bool = False
    ) -> Dict:
        """Envia mensagem em uma conversa"""
        return await self._request(
            "POST",
            f"/conversations/{conversation_id}/messages",
            json={
                "content": content,
                "message_type": message_type,
                "private": private
            }
        )

    async def update_conversation(
        self,
        conversation_id: int,
        status: Optional[str] = None,
        assignee_id: Optional[int] = None,
        labels: Optional[List[str]] = None
    ) -> Dict:
        """Atualiza uma conversa"""
        data = {}
        if status:
            data["status"] = status
        if assignee_id is not None:
            data["assignee_id"] = assignee_id
        if labels is not None:
            data["labels"] = labels

        return await self._request(
            "PATCH",
            f"/conversations/{conversation_id}",
            json=data
        )

    async def toggle_conversation_status(self, conversation_id: int, status: str) -> Dict:
        """Altera status da conversa"""
        return await self._request(
            "POST",
            f"/conversations/{conversation_id}/toggle_status",
            json={"status": status}
        )

    # ===== Contacts =====

    async def search_contacts(self, query: str) -> Dict:
        """Busca contatos"""
        return await self._request("GET", "/contacts/search", params={"q": query})

    async def get_contact(self, contact_id: int) -> Dict:
        """Obtém detalhes de um contato"""
        return await self._request("GET", f"/contacts/{contact_id}")

    async def create_contact(
        self,
        name: str,
        phone_number: Optional[str] = None,
        email: Optional[str] = None,
        inbox_id: Optional[int] = None
    ) -> Dict:
        """Cria um novo contato"""
        data = {"name": name}
        if phone_number:
            data["phone_number"] = phone_number
        if email:
            data["email"] = email
        if inbox_id:
            data["inbox_id"] = inbox_id

        return await self._request("POST", "/contacts", json=data)

    # ===== Inboxes =====

    async def get_inboxes(self) -> List[Dict]:
        """Lista inboxes"""
        result = await self._request("GET", "/inboxes")
        return result.get("payload", result) if isinstance(result, dict) else result

    async def get_inbox(self, inbox_id: int) -> Dict:
        """Obtém detalhes de uma inbox"""
        return await self._request("GET", f"/inboxes/{inbox_id}")

    # ===== Labels =====

    async def get_labels(self) -> List[Dict]:
        """Lista labels"""
        result = await self._request("GET", "/labels")
        return result.get("payload", result) if isinstance(result, dict) else result

    # ===== Teams =====

    async def get_teams(self) -> List[Dict]:
        """Lista teams"""
        result = await self._request("GET", "/teams")
        return result.get("payload", result) if isinstance(result, dict) else result

    # ===== Agents =====

    async def get_agents(self) -> List[Dict]:
        """Lista agentes"""
        result = await self._request("GET", "/agents")
        return result.get("payload", result) if isinstance(result, dict) else result

    # ===== Webhooks =====

    async def get_webhooks(self) -> List[Dict]:
        """Lista webhooks"""
        result = await self._request("GET", "/webhooks")
        # Normalizar resposta
        if isinstance(result, list):
            return result
        elif isinstance(result, dict):
            if "payload" in result and isinstance(result["payload"], list):
                return result["payload"]
            return list(result.values()) if result else []
        return []

    async def create_webhook(self, url: str, subscriptions: Optional[List[str]] = None) -> Dict:
        """Cria webhook"""
        data = {
            "webhook": {
                "url": url,
                "subscriptions": subscriptions or ["message_created"]
            }
        }
        return await self._request("POST", "/webhooks", json=data)

    async def update_webhook(
        self,
        webhook_id: int,
        url: str,
        subscriptions: Optional[List[str]] = None
    ) -> Dict:
        """Atualiza webhook"""
        data = {
            "webhook": {
                "url": url,
                "subscriptions": subscriptions or ["message_created"]
            }
        }
        return await self._request("PATCH", f"/webhooks/{webhook_id}", json=data)

    async def delete_webhook(self, webhook_id: int) -> Dict:
        """Remove webhook"""
        return await self._request("DELETE", f"/webhooks/{webhook_id}")

    # ===== Profile =====

    async def get_profile(self) -> Dict:
        """Obtém perfil do usuário autenticado"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{self.base_url}/api/v1/profile",
                headers=self.headers
            )
            response.raise_for_status()
            return response.json()
