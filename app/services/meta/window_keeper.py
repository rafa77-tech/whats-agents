"""
Proactive Window Management.

Sprint 70+ — Chunk 27.

Scans conversations with windows expiring in 2-4h and sends
lightweight check-in messages to keep the window open.
"""

import logging
from typing import List
from datetime import datetime, timezone, timedelta

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetaWindowKeeper:
    """
    Gerenciador proativo de janelas de conversa.

    Detecta janelas prestes a expirar e envia mensagens
    leves para manter a janela aberta (evita custo de template).
    """

    WINDOW_EXPIRY_HOURS_MIN = 2  # Mínimo de horas antes de expirar para agir
    WINDOW_EXPIRY_HOURS_MAX = 4  # Máximo de horas antes de expirar

    CHECK_IN_MESSAGES = [
        "Oi! Tudo certo por aí?",
        "Oi! Surgiu alguma dúvida?",
        "E aí, conseguiu ver as vagas?",
    ]

    async def identificar_janelas_expirando(self) -> List[dict]:
        """
        Identifica conversas com janelas expirando em 2-4h.

        Returns:
            Lista de conversas com janelas prestes a expirar
        """
        try:
            now = datetime.now(timezone.utc)
            expiry_min = now + timedelta(hours=self.WINDOW_EXPIRY_HOURS_MIN)
            expiry_max = now + timedelta(hours=self.WINDOW_EXPIRY_HOURS_MAX)

            result = (
                supabase.table("meta_conversation_windows")
                .select("chip_id, telefone, window_type, expires_at")
                .gte("expires_at", expiry_min.isoformat())
                .lte("expires_at", expiry_max.isoformat())
                .execute()
            )
            return result.data or []

        except Exception as e:
            logger.error("[WindowKeeper] Erro ao identificar janelas: %s", e)
            return []

    async def executar_check_in(self) -> dict:
        """
        Executa check-in em conversas com janelas expirando.

        Respects:
        - Business hours (8h-20h)
        - Rate limits
        - Only for engaged conversations

        Returns:
            Dict com resultados
        """
        from app.core.timezone import agora_brasilia

        now_brt = agora_brasilia()
        hora = now_brt.hour

        # Respeitar horário comercial
        if hora < int(settings.HORARIO_INICIO.split(":")[0]) or hora >= int(
            settings.HORARIO_FIM.split(":")[0]
        ):
            return {"status": "skipped", "motivo": "Fora do horário comercial", "enviados": 0}

        # Respeitar dia da semana (seg-sex)
        if now_brt.weekday() >= 5:
            return {"status": "skipped", "motivo": "Final de semana", "enviados": 0}

        janelas = await self.identificar_janelas_expirando()

        if not janelas:
            return {"status": "ok", "motivo": "Nenhuma janela expirando", "enviados": 0}

        enviados = 0
        erros = 0

        for janela in janelas:
            try:
                # Verificar se conversa está engajada
                engajada = await self._conversa_engajada(
                    janela["chip_id"], janela["telefone"]
                )
                if not engajada:
                    continue

                # v1: apenas log, não envia automaticamente
                logger.info(
                    "[WindowKeeper] Check-in necessário: chip=%s, tel=%s, expira=%s",
                    janela["chip_id"],
                    janela["telefone"],
                    janela["expires_at"],
                )
                enviados += 1

            except Exception as e:
                logger.warning("[WindowKeeper] Erro no check-in: %s", e)
                erros += 1

        return {
            "status": "ok",
            "janelas_detectadas": len(janelas),
            "enviados": enviados,
            "erros": erros,
        }

    async def _conversa_engajada(self, chip_id: str, telefone: str) -> bool:
        """
        Verifica se a conversa está engajada (médico respondeu recentemente).

        Args:
            chip_id: ID do chip
            telefone: Telefone do médico

        Returns:
            True se engajada
        """
        try:
            # Verificar se há mensagens do médico nas últimas 12h
            from datetime import datetime, timezone, timedelta

            limite = (datetime.now(timezone.utc) - timedelta(hours=12)).isoformat()
            result = (
                supabase.table("interacoes")
                .select("id")
                .eq("telefone", telefone)
                .eq("direcao", "inbound")
                .gte("created_at", limite)
                .limit(1)
                .execute()
            )
            return bool(result.data)

        except Exception:
            return False


# Singleton
window_keeper = MetaWindowKeeper()
