"""
Meta Conversation Window Tracker — Rastreia janelas de 24h.

Sprint 66 — Dentro da janela: free-form. Fora: template obrigatório.
"""

import logging
from datetime import datetime, timedelta, timezone

from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Duração das janelas por tipo
WINDOW_DURATIONS = {
    "user_initiated": timedelta(hours=24),
    "click_to_whatsapp": timedelta(hours=72),
}


class MetaWindowTracker:
    """Rastreia janelas de conversa 24h da Meta."""

    async def esta_na_janela(self, chip_id: str, telefone: str) -> bool:
        """
        Verifica se há janela de conversa ativa.

        Args:
            chip_id: ID do chip Meta
            telefone: Número do destinatário

        Returns:
            True se janela ativa (pode enviar free-form)
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = (
                supabase.table("meta_conversation_windows")
                .select("id")
                .eq("chip_id", chip_id)
                .eq("telefone", telefone)
                .gt("window_expires_at", now)
                .limit(1)
                .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.warning(f"[WindowTracker] Erro ao verificar janela: {e}")
            # Na dúvida, assume fora da janela (conservador)
            return False

    async def abrir_janela(
        self,
        chip_id: str,
        telefone: str,
        tipo: str = "user_initiated",
    ) -> None:
        """
        Abre ou renova janela de conversa.

        Chamado quando mensagem recebida do usuário (webhook_meta).

        Args:
            chip_id: ID do chip Meta
            telefone: Número do remetente
            tipo: Tipo da janela (user_initiated, click_to_whatsapp)
        """
        now = datetime.now(timezone.utc)
        duration = WINDOW_DURATIONS.get(tipo, timedelta(hours=24))
        expires = now + duration

        try:
            supabase.table("meta_conversation_windows").upsert(
                {
                    "chip_id": chip_id,
                    "telefone": telefone,
                    "window_opened_at": now.isoformat(),
                    "window_expires_at": expires.isoformat(),
                    "window_type": tipo,
                    "created_at": now.isoformat(),
                },
                on_conflict="chip_id,telefone",
            ).execute()

            logger.debug(
                f"[WindowTracker] Janela aberta: chip={chip_id[:8]}, "
                f"tel={telefone[-4:]}, expira={expires.isoformat()}"
            )
        except Exception as e:
            logger.error(f"[WindowTracker] Erro ao abrir janela: {e}")

    async def limpar_janelas_expiradas(self) -> int:
        """
        Remove janelas expiradas do banco.

        Deve ser chamado periodicamente por um job.

        Returns:
            Número de janelas removidas
        """
        try:
            now = datetime.now(timezone.utc).isoformat()
            result = (
                supabase.table("meta_conversation_windows")
                .delete()
                .lt("window_expires_at", now)
                .execute()
            )
            count = len(result.data) if result.data else 0
            if count > 0:
                logger.info(
                    f"[WindowTracker] {count} janelas expiradas removidas"
                )
            return count
        except Exception as e:
            logger.error(f"[WindowTracker] Erro ao limpar janelas: {e}")
            return 0


# Singleton
window_tracker = MetaWindowTracker()
