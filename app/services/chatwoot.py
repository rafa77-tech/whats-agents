"""
Servico para consultas ao Chatwoot.

IMPORTANTE: A integracao nativa Evolution API <-> Chatwoot ja faz
a sincronizacao de mensagens/contatos/conversas. Este servico
e apenas para CONSULTA de IDs e processamento de webhooks.
"""
import httpx
import logging
from typing import Optional

from app.core.config import settings
from app.services.supabase import get_supabase

logger = logging.getLogger(__name__)


class ChatwootService:
    """
    Servico para consultas ao Chatwoot.

    NAO usar para criar contatos, conversas ou enviar mensagens.
    A integracao nativa Evolution API <-> Chatwoot ja faz isso.
    """

    def __init__(self):
        self.base_url = settings.CHATWOOT_URL.rstrip("/")
        self.api_token = settings.CHATWOOT_API_KEY
        self.account_id = settings.CHATWOOT_ACCOUNT_ID

    @property
    def headers(self) -> dict:
        return {
            "api_access_token": self.api_token,
            "Content-Type": "application/json"
        }

    @property
    def configurado(self) -> bool:
        """Verifica se Chatwoot esta configurado."""
        return bool(self.base_url and self.api_token)

    async def buscar_contato_por_telefone(self, telefone: str) -> Optional[dict]:
        """
        Busca contato no Chatwoot pelo telefone.

        Args:
            telefone: Telefone no formato internacional (ex: 5511999999999)

        Returns:
            Dados do contato ou None se nao encontrado
        """
        if not self.configurado:
            logger.warning("Chatwoot nao configurado")
            return None

        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/search"

        # Chatwoot pode ter o telefone com ou sem +
        queries = [telefone, f"+{telefone}"]

        async with httpx.AsyncClient(timeout=10.0) as client:
            for query in queries:
                try:
                    response = await client.get(
                        url,
                        params={"q": query},
                        headers=self.headers
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("payload"):
                        return data["payload"][0]
                except httpx.HTTPError as e:
                    logger.warning(f"Erro HTTP ao buscar contato {query}: {e}")
                except Exception as e:
                    logger.warning(f"Erro ao buscar contato {query}: {e}")

        return None

    async def buscar_conversas_do_contato(self, contact_id: int) -> list[dict]:
        """
        Busca conversas de um contato no Chatwoot.

        Args:
            contact_id: ID do contato no Chatwoot

        Returns:
            Lista de conversas
        """
        if not self.configurado:
            return []

        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/contacts/{contact_id}/conversations"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                return data.get("payload", [])
            except Exception as e:
                logger.error(f"Erro ao buscar conversas do contato {contact_id}: {e}")
                return []

    async def buscar_conversa_por_id(self, conversation_id: int) -> Optional[dict]:
        """
        Busca conversa especifica no Chatwoot.

        Args:
            conversation_id: ID da conversa no Chatwoot

        Returns:
            Dados da conversa ou None
        """
        if not self.configurado:
            return None

        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/conversations/{conversation_id}"
        )

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Erro ao buscar conversa {conversation_id}: {e}")
                return None

    async def enviar_mensagem(
        self,
        conversation_id: int,
        content: str,
        message_type: str = "outgoing"
    ) -> bool:
        """
        Envia mensagem para uma conversa no Chatwoot.

        NOTA: A integracao nativa Evolution API <-> Chatwoot ja sincroniza
        mensagens automaticamente. Este metodo e apenas para casos especiais
        como mensagens de transicao de handoff.

        Args:
            conversation_id: ID da conversa no Chatwoot
            content: Conteudo da mensagem
            message_type: "incoming" ou "outgoing"

        Returns:
            True se enviou com sucesso
        """
        if not self.configurado:
            logger.warning("Chatwoot nao configurado, ignorando envio de mensagem")
            return False

        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/conversations/{conversation_id}/messages"
        )

        payload = {
            "content": content,
            "message_type": message_type
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                logger.info(f"Mensagem enviada para Chatwoot conversa {conversation_id}")
                return True
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para Chatwoot: {e}")
                return False


# Instancia global
chatwoot_service = ChatwootService()


async def sincronizar_ids_chatwoot(cliente_id: str, telefone: str) -> dict:
    """
    Busca IDs do Chatwoot e salva no nosso banco.

    Chamado quando precisamos do mapeamento (ex: antes de processar webhook).

    Args:
        cliente_id: ID do cliente no nosso banco
        telefone: Telefone do cliente

    Returns:
        Dict com chatwoot_contact_id e chatwoot_conversation_id
    """
    supabase = get_supabase()
    resultado = {
        "chatwoot_contact_id": None,
        "chatwoot_conversation_id": None
    }

    # Buscar contato no Chatwoot
    contato = await chatwoot_service.buscar_contato_por_telefone(telefone)

    if not contato:
        logger.warning(f"Contato nao encontrado no Chatwoot: {telefone}")
        return resultado

    resultado["chatwoot_contact_id"] = contato["id"]

    # Atualizar cliente com chatwoot_contact_id
    try:
        supabase.table("clientes").update({
            "chatwoot_contact_id": str(contato["id"])
        }).eq("id", cliente_id).execute()
    except Exception as e:
        logger.error(f"Erro ao atualizar chatwoot_contact_id: {e}")

    # Buscar conversa mais recente
    conversas = await chatwoot_service.buscar_conversas_do_contato(contato["id"])

    if conversas:
        # Pegar a conversa mais recente (primeira da lista)
        conversa_chatwoot = conversas[0]
        resultado["chatwoot_conversation_id"] = conversa_chatwoot["id"]

        # Atualizar nossa conversa ativa
        try:
            supabase.table("conversations").update({
                "chatwoot_conversation_id": str(conversa_chatwoot["id"])
            }).eq("cliente_id", cliente_id).eq("status", "active").execute()
        except Exception as e:
            logger.error(f"Erro ao atualizar chatwoot_conversation_id: {e}")

    logger.info(
        f"IDs Chatwoot sincronizados: contact={resultado['chatwoot_contact_id']}, "
        f"conversation={resultado['chatwoot_conversation_id']}"
    )

    return resultado
