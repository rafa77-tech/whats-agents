"""
WhatsApp Flows Service — CRUD + webhook processing.

Sprint 68 — Epic 68.2: Native forms in WhatsApp (JSON v7.0).
Create, publish, send, receive encrypted responses.
"""

import json
import logging
from typing import Optional, List
from datetime import datetime, timezone

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

_GRAPH_API_BASE = "https://graph.facebook.com"


class MetaFlowService:
    """
    Serviço de gerenciamento de WhatsApp Flows.

    Flows permitem formulários nativos dentro do WhatsApp,
    com criptografia end-to-end das respostas.
    """

    @property
    def api_version(self) -> str:
        return settings.META_GRAPH_API_VERSION or "v21.0"

    async def _obter_access_token(self, waba_id: str) -> Optional[str]:
        """Busca access_token do banco via waba_id."""
        try:
            result = (
                supabase.table("chips")
                .select("meta_access_token")
                .eq("meta_waba_id", waba_id)
                .not_.is_("meta_access_token", "null")
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0].get("meta_access_token")
            return None
        except Exception as e:
            logger.error("[MetaFlow] Erro ao buscar access_token: %s", e)
            return None

    async def criar_flow(
        self,
        waba_id: str,
        name: str,
        flow_type: str = "FLOW",
        categories: Optional[List[str]] = None,
    ) -> dict:
        """
        Cria um Flow na Meta via Graph API.

        Args:
            waba_id: WABA ID
            name: Nome do Flow
            flow_type: Tipo (FLOW)
            categories: Categorias (ex: ["SURVEY", "LEAD_GENERATION"])

        Returns:
            Dict com resultado
        """
        from app.services.http_client import get_http_client

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": f"Access token não encontrado para WABA {waba_id}"}

        url = f"{_GRAPH_API_BASE}/{self.api_version}/{waba_id}/flows"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        payload = {"name": name, "flow_type": flow_type}
        if categories:
            payload["categories"] = categories

        try:
            client = await get_http_client()
            response = await client.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            meta_flow_id = str(data.get("id", ""))

            # Salvar no banco
            now = datetime.now(timezone.utc).isoformat()
            row = {
                "waba_id": waba_id,
                "meta_flow_id": meta_flow_id,
                "name": name,
                "flow_type": flow_type,
                "status": "DRAFT",
                "created_at": now,
                "updated_at": now,
            }
            supabase.table("meta_flows").insert(row).execute()

            return {"success": True, "flow_id": meta_flow_id, "status": "DRAFT"}

        except Exception as e:
            logger.error("[MetaFlow] Erro ao criar flow '%s': %s", name, e)
            return {"success": False, "error": "Erro interno ao criar flow"}

    async def publicar_flow(self, waba_id: str, flow_id: str) -> dict:
        """
        Publica um Flow (DRAFT → PUBLISHED).

        Args:
            waba_id: WABA ID
            flow_id: Meta Flow ID

        Returns:
            Dict com resultado
        """
        from app.services.http_client import get_http_client

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": "Access token não encontrado"}

        url = f"{_GRAPH_API_BASE}/{self.api_version}/{flow_id}/publish"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            client = await get_http_client()
            response = await client.post(url, headers=headers, timeout=30)
            response.raise_for_status()

            # Atualizar status no banco
            supabase.table("meta_flows").update(
                {"status": "PUBLISHED", "updated_at": datetime.now(timezone.utc).isoformat()}
            ).eq("meta_flow_id", flow_id).execute()

            return {"success": True, "status": "PUBLISHED"}

        except Exception as e:
            logger.error("[MetaFlow] Erro ao publicar flow %s: %s", flow_id, e)
            return {"success": False, "error": "Erro interno ao publicar flow"}

    async def listar_flows(self, waba_id: str) -> List[dict]:
        """
        Lista flows do banco local.

        Args:
            waba_id: WABA ID

        Returns:
            Lista de flows
        """
        try:
            result = (
                supabase.table("meta_flows")
                .select("*")
                .eq("waba_id", waba_id)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.error("[MetaFlow] Erro ao listar flows: %s", e)
            return []

    async def buscar_flow(self, flow_id: str) -> Optional[dict]:
        """
        Busca flow por ID.

        Args:
            flow_id: Meta Flow ID

        Returns:
            Flow ou None
        """
        try:
            result = (
                supabase.table("meta_flows")
                .select("*")
                .eq("meta_flow_id", flow_id)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error("[MetaFlow] Erro ao buscar flow %s: %s", flow_id, e)
            return None

    async def deprecar_flow(self, waba_id: str, flow_id: str) -> dict:
        """
        Depreca um Flow (PUBLISHED → DEPRECATED).

        Args:
            waba_id: WABA ID
            flow_id: Meta Flow ID

        Returns:
            Dict com resultado
        """
        from app.services.http_client import get_http_client

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": "Access token não encontrado"}

        url = f"{_GRAPH_API_BASE}/{self.api_version}/{flow_id}"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            client = await get_http_client()
            response = await client.delete(url, headers=headers, timeout=30)
            response.raise_for_status()

            supabase.table("meta_flows").update(
                {"status": "DEPRECATED", "updated_at": datetime.now(timezone.utc).isoformat()}
            ).eq("meta_flow_id", flow_id).execute()

            return {"success": True, "status": "DEPRECATED"}

        except Exception as e:
            logger.error("[MetaFlow] Erro ao deprecar flow %s: %s", flow_id, e)
            return {"success": False, "error": "Erro interno ao deprecar flow"}

    async def atualizar_flow(
        self,
        waba_id: str,
        flow_id: str,
        json_definition: dict,
    ) -> dict:
        """
        Atualiza a definição JSON de um Flow.

        Args:
            waba_id: WABA ID
            flow_id: Meta Flow ID
            json_definition: Definição JSON do flow (v7.0)

        Returns:
            Dict com resultado
        """
        from app.services.http_client import get_http_client

        access_token = await self._obter_access_token(waba_id)
        if not access_token:
            return {"success": False, "error": "Access token não encontrado"}

        url = f"{_GRAPH_API_BASE}/{self.api_version}/{flow_id}/assets"
        headers = {"Authorization": f"Bearer {access_token}"}

        try:
            client = await get_http_client()
            response = await client.post(
                url,
                headers=headers,
                files={"file": ("flow.json", json.dumps(json_definition), "application/json")},
                data={"name": "flow.json", "asset_type": "FLOW_JSON"},
                timeout=30,
            )
            response.raise_for_status()

            # Atualizar banco
            supabase.table("meta_flows").update(
                {
                    "json_definition": json_definition,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("meta_flow_id", flow_id).execute()

            return {"success": True}

        except Exception as e:
            logger.error("[MetaFlow] Erro ao atualizar flow %s: %s", flow_id, e)
            return {"success": False, "error": "Erro interno ao atualizar flow"}

    async def decriptar_resposta_flow(self, encrypted_response: dict) -> Optional[dict]:
        """
        Decripta resposta de Flow usando AES-128-GCM.

        Sprint 70 — Epic 70.4: Implementação real da decriptação.

        Formato do encrypted_flow_data (base64):
        - Primeiros 12 bytes: IV (nonce)
        - Últimos 16 bytes: Auth Tag (GCM)
        - Meio: Ciphertext

        Args:
            encrypted_response: Dict com encrypted_flow_data

        Returns:
            Dict com dados decriptados ou None em caso de erro
        """
        private_key_hex = settings.META_FLOW_PRIVATE_KEY
        if not private_key_hex:
            logger.warning("[MetaFlow] FLOW_PRIVATE_KEY não configurada, retornando dados raw")
            return encrypted_response

        encrypted_data = encrypted_response.get("encrypted_flow_data")
        if not encrypted_data:
            return encrypted_response

        try:
            import base64
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM

            # Decodificar chave (hex -> bytes, 16 bytes para AES-128)
            key = bytes.fromhex(private_key_hex)

            # Decodificar payload base64
            raw = base64.b64decode(encrypted_data)

            # Extrair IV (12 bytes), ciphertext, tag (16 bytes)
            iv = raw[:12]
            tag = raw[-16:]
            ciphertext = raw[12:-16]

            # AES-GCM: ciphertext + tag concatenados para a lib cryptography
            aesgcm = AESGCM(key)
            plaintext = aesgcm.decrypt(iv, ciphertext + tag, None)

            # Parse JSON
            decrypted = json.loads(plaintext.decode("utf-8"))

            logger.info("[MetaFlow] Flow response decriptada com sucesso")
            return decrypted

        except Exception as e:
            logger.error("[MetaFlow] Erro ao decriptar flow response: %s", e)
            return None

    async def processar_resposta_flow(
        self,
        flow_token: str,
        response_data: dict,
        telefone: str,
    ) -> dict:
        """
        Processa resposta de um Flow.

        Args:
            flow_token: Token do flow (identifica a sessão)
            response_data: Dados da resposta
            telefone: Número do respondente

        Returns:
            Dict com resultado do processamento
        """
        try:
            # Salvar resposta no banco
            row = {
                "flow_token": flow_token,
                "telefone": telefone,
                "response_data": response_data,
                "processed": False,
            }
            supabase.table("meta_flow_responses").insert(row).execute()

            # Determinar tipo de flow e rotear
            flow_type = response_data.get("flow_type", "")

            if flow_type == "onboarding":
                return await self._processar_onboarding(response_data, telefone)
            elif flow_type == "confirmacao":
                return await self._processar_confirmacao(response_data, telefone)
            elif flow_type == "avaliacao":
                return await self._processar_avaliacao(response_data, telefone)
            else:
                logger.info("[MetaFlow] Tipo de flow desconhecido: %s", flow_type)
                return {"success": True, "tipo": "unknown", "processado": False}

        except Exception as e:
            logger.error("[MetaFlow] Erro ao processar resposta: %s", e)
            return {"success": False, "error": "Erro interno ao processar resposta"}

    async def _processar_onboarding(self, data: dict, telefone: str) -> dict:
        """Processa resposta de flow de onboarding."""
        logger.info("[MetaFlow] Processando onboarding para ***%s", telefone[-4:])
        return {"success": True, "tipo": "onboarding", "processado": True}

    async def _processar_confirmacao(self, data: dict, telefone: str) -> dict:
        """Processa resposta de flow de confirmação de plantão."""
        logger.info("[MetaFlow] Processando confirmação para ***%s", telefone[-4:])
        return {"success": True, "tipo": "confirmacao", "processado": True}

    async def _processar_avaliacao(self, data: dict, telefone: str) -> dict:
        """Processa resposta de flow de avaliação pós-plantão."""
        logger.info("[MetaFlow] Processando avaliação para ***%s", telefone[-4:])
        return {"success": True, "tipo": "avaliacao", "processado": True}


# Singleton
flow_service = MetaFlowService()
