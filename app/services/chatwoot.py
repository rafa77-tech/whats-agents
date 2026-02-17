"""
Servico para consultas ao Chatwoot.

IMPORTANTE: A integracao nativa Evolution API <-> Chatwoot ja faz
a sincronizacao de mensagens/contatos/conversas. Este servico
e apenas para CONSULTA de IDs e processamento de webhooks.
"""

import logging
from typing import Optional

from app.core.config import settings
from app.services.http_client import get_http_client
from app.services.supabase import supabase

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
        return {"api_access_token": self.api_token, "Content-Type": "application/json"}

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

        client = await get_http_client()
        for query in queries:
            try:
                response = await client.get(
                    url, params={"q": query}, headers=self.headers, timeout=10.0
                )
                response.raise_for_status()
                data = response.json()

                if data.get("payload"):
                    return data["payload"][0]
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
            f"{self.base_url}/api/v1/accounts/{self.account_id}/contacts/{contact_id}/conversations"
        )

        try:
            client = await get_http_client()
            response = await client.get(url, headers=self.headers, timeout=10.0)
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

        url = f"{self.base_url}/api/v1/accounts/{self.account_id}/conversations/{conversation_id}"

        try:
            client = await get_http_client()
            response = await client.get(url, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Erro ao buscar conversa {conversation_id}: {e}")
            return None

    async def buscar_telefone_por_conversation_id(self, conversation_id: int) -> Optional[str]:
        """
        Busca telefone do contato a partir do ID da conversa.

        Usado para resolver telefone quando mensagem vem em formato LID
        (sem remoteJidAlt) mas temos o chatwoot_conversation_id.

        Args:
            conversation_id: ID da conversa no Chatwoot

        Returns:
            Telefone no formato internacional (ex: 5511999999999) ou None
        """
        conversa = await self.buscar_conversa_por_id(conversation_id)
        if not conversa:
            return None

        # Estrutura: conversa.meta.sender.phone_number
        meta = conversa.get("meta", {})
        sender = meta.get("sender", {})
        phone = sender.get("phone_number")

        if phone:
            # Remover caracteres não numéricos (ex: +55 11 99999-9999 -> 5511999999999)
            phone_clean = "".join(c for c in phone if c.isdigit())
            if len(phone_clean) >= 10:
                logger.info(
                    f"Telefone resolvido via Chatwoot conversation {conversation_id}: {phone_clean[:6]}..."
                )
                return phone_clean

        logger.warning(f"Telefone nao encontrado na conversa Chatwoot {conversation_id}")
        return None

    async def enviar_mensagem(
        self, conversation_id: int, content: str, message_type: str = "outgoing"
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

        payload = {"content": content, "message_type": message_type}

        try:
            client = await get_http_client()
            response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Mensagem enviada para Chatwoot conversa {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem para Chatwoot: {e}")
            return False

    async def adicionar_label(self, conversation_id: int, label: str) -> bool:
        """
        Adiciona uma label a uma conversa no Chatwoot.

        Args:
            conversation_id: ID da conversa no Chatwoot
            label: Nome da label (ex: "humano")

        Returns:
            True se adicionou com sucesso
        """
        if not self.configurado:
            logger.warning("Chatwoot nao configurado, ignorando adicao de label")
            return False

        # Primeiro buscar labels atuais
        conversa = await self.buscar_conversa_por_id(conversation_id)
        if not conversa:
            logger.error(f"Conversa {conversation_id} nao encontrada no Chatwoot")
            return False

        labels_atuais = conversa.get("labels", [])

        # Se label ja existe, nao precisa adicionar
        if label in labels_atuais:
            logger.debug(f"Label '{label}' ja existe na conversa {conversation_id}")
            return True

        # Adicionar nova label
        novas_labels = labels_atuais + [label]

        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/conversations/{conversation_id}/labels"
        )

        payload = {"labels": novas_labels}

        try:
            client = await get_http_client()
            response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Label '{label}' adicionada a conversa {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao adicionar label no Chatwoot: {e}")
            return False

    async def remover_label(self, conversation_id: int, label: str) -> bool:
        """
        Remove uma label de uma conversa no Chatwoot.

        Args:
            conversation_id: ID da conversa no Chatwoot
            label: Nome da label a remover (ex: "humano")

        Returns:
            True se removeu com sucesso
        """
        if not self.configurado:
            logger.warning("Chatwoot nao configurado, ignorando remocao de label")
            return False

        # Primeiro buscar labels atuais
        conversa = await self.buscar_conversa_por_id(conversation_id)
        if not conversa:
            logger.error(f"Conversa {conversation_id} nao encontrada no Chatwoot")
            return False

        labels_atuais = conversa.get("labels", [])

        # Se label nao existe, nao precisa remover
        if label not in labels_atuais:
            logger.debug(f"Label '{label}' nao existe na conversa {conversation_id}")
            return True

        # Remover label
        novas_labels = [lbl for lbl in labels_atuais if lbl != label]

        url = (
            f"{self.base_url}/api/v1/accounts/{self.account_id}"
            f"/conversations/{conversation_id}/labels"
        )

        payload = {"labels": novas_labels}

        try:
            client = await get_http_client()
            response = await client.post(url, json=payload, headers=self.headers, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Label '{label}' removida da conversa {conversation_id}")
            return True
        except Exception as e:
            logger.error(f"Erro ao remover label no Chatwoot: {e}")
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
    resultado = {"chatwoot_contact_id": None, "chatwoot_conversation_id": None}

    # Buscar contato no Chatwoot
    contato = await chatwoot_service.buscar_contato_por_telefone(telefone)

    if not contato:
        logger.warning(f"Contato nao encontrado no Chatwoot: {telefone}")
        return resultado

    resultado["chatwoot_contact_id"] = contato["id"]

    # Atualizar cliente com chatwoot_contact_id
    try:
        supabase.table("clientes").update({"chatwoot_contact_id": str(contato["id"])}).eq(
            "id", cliente_id
        ).execute()
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
            supabase.table("conversations").update(
                {"chatwoot_conversation_id": str(conversa_chatwoot["id"])}
            ).eq("cliente_id", cliente_id).eq("status", "active").execute()
        except Exception as e:
            logger.error(f"Erro ao atualizar chatwoot_conversation_id: {e}")

    logger.info(
        f"IDs Chatwoot sincronizados: contact={resultado['chatwoot_contact_id']}, "
        f"conversation={resultado['chatwoot_conversation_id']}"
    )

    return resultado
