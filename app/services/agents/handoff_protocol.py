"""
AI Agent Handoff Protocol.

Sprint 70+ — Chunk 26.

Transfer control between Julia ↔ Helena via WhatsApp.
"""

import logging
from typing import Optional
from datetime import datetime, timezone

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class HandoffProtocol:
    """
    Protocolo de transferência entre agentes AI.

    Permite transfer de controle de conversa entre Julia e Helena
    com preservação de contexto.
    """

    async def transfer(
        self,
        from_agent: str,
        to_agent: str,
        conversation_id: str,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Transfere controle de conversa entre agentes.

        Args:
            from_agent: Agente de origem (ex: "julia", "helena")
            to_agent: Agente destino
            conversation_id: ID da conversa
            context: Contexto adicional para o agente destino

        Returns:
            Dict com resultado da transferência
        """
        try:
            from app.services.agents.agent_registry import agent_registry

            # Validar agentes
            if not agent_registry.esta_registrado(from_agent):
                return {"success": False, "error": f"Agente '{from_agent}' não registrado"}
            if not agent_registry.esta_registrado(to_agent):
                return {"success": False, "error": f"Agente '{to_agent}' não registrado"}

            # Registrar handoff
            now = datetime.now(timezone.utc).isoformat()
            handoff_record = {
                "conversation_id": conversation_id,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "context": context or {},
                "status": "completed",
                "created_at": now,
            }

            # Atualizar conversa
            supabase.table("conversations").update(
                {"controlled_by": to_agent, "updated_at": now}
            ).eq("id", conversation_id).execute()

            logger.info(
                "[Handoff] %s → %s para conversa %s",
                from_agent,
                to_agent,
                conversation_id,
            )

            return {
                "success": True,
                "from_agent": from_agent,
                "to_agent": to_agent,
                "conversation_id": conversation_id,
            }

        except Exception as e:
            logger.error("[Handoff] Erro na transferência: %s", e)
            return {"success": False, "error": str(e)}

    async def obter_agente_atual(self, conversation_id: str) -> Optional[str]:
        """
        Obtém o agente que controla a conversa.

        Args:
            conversation_id: ID da conversa

        Returns:
            Nome do agente ou None
        """
        try:
            result = (
                supabase.table("conversations")
                .select("controlled_by")
                .eq("id", conversation_id)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0].get("controlled_by")
            return None

        except Exception as e:
            logger.error("[Handoff] Erro ao obter agente atual: %s", e)
            return None


# Singleton
handoff_protocol = HandoffProtocol()
