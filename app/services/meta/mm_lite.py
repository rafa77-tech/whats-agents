"""
MM Lite (Marketing Messages Lite) Service.

Sprint 68 — Epic 68.1: Meta's AI-optimized marketing delivery.
+9% delivery rate — Meta decides WHEN to deliver.

Decision logic:
- Campaigns (volume) → MM Lite
- Urgent (confirmations, time-sensitive) → Regular
"""

import logging
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MMLiteService:
    """
    Serviço de Marketing Messages Lite (MM Lite).

    MM Lite permite que a Meta otimize o momento de entrega
    de mensagens de marketing, resultando em +9% delivery rate.
    """

    async def verificar_elegibilidade(self, waba_id: str) -> dict:
        """
        Verifica se WABA é elegível para MM Lite.

        Args:
            waba_id: WABA ID

        Returns:
            Dict com elegivel, motivo, tier
        """
        if not settings.META_MM_LITE_ENABLED:
            return {
                "elegivel": False,
                "motivo": "MM Lite desabilitado na configuração",
                "tier": None,
            }

        try:
            result = (
                supabase.table("chips")
                .select("id, meta_waba_id, meta_access_token, status")
                .eq("meta_waba_id", waba_id)
                .not_.is_("meta_access_token", "null")
                .limit(1)
                .execute()
            )

            if not result.data:
                return {
                    "elegivel": False,
                    "motivo": f"WABA {waba_id} não encontrada",
                    "tier": None,
                }

            chip = result.data[0]
            if chip.get("status") != "active":
                return {
                    "elegivel": False,
                    "motivo": f"Chip não está ativo (status: {chip.get('status')})",
                    "tier": None,
                }

            return {
                "elegivel": True,
                "motivo": "WABA ativa com MM Lite habilitado",
                "tier": "STANDARD",
            }

        except Exception as e:
            logger.error("Erro ao verificar elegibilidade MM Lite: %s", e)
            return {"elegivel": False, "motivo": str(e), "tier": None}

    async def esta_habilitado(self, waba_id: str) -> bool:
        """
        Verifica se MM Lite está habilitado para a WABA.

        Args:
            waba_id: WABA ID

        Returns:
            True se habilitado
        """
        result = await self.verificar_elegibilidade(waba_id)
        return result["elegivel"]

    def deve_usar_mm_lite(self, contexto: dict) -> bool:
        """
        Decide se deve usar MM Lite com base no contexto.

        Regras:
        - Campanhas de marketing (volume) → MM Lite
        - Confirmações, urgentes → Regular
        - Mensagens individuais → Regular

        Args:
            contexto: Dict com tipo, urgente, campanha_id, etc.

        Returns:
            True se deve usar MM Lite
        """
        if not settings.META_MM_LITE_ENABLED:
            return False

        tipo = contexto.get("tipo", "")
        urgente = contexto.get("urgente", False)
        campanha_id = contexto.get("campanha_id")

        # Nunca usar MM Lite para mensagens urgentes
        if urgente:
            return False

        # Confirmações sempre regular
        if tipo in ("confirmacao", "confirmation", "utility", "authentication"):
            return False

        # Campanhas de marketing → MM Lite
        if campanha_id and tipo in ("marketing", "campanha", ""):
            return True

        # Default: regular
        return False

    async def registrar_envio_mm_lite(
        self,
        chip_id: str,
        waba_id: str,
        telefone: str,
        template_name: str,
    ) -> Optional[dict]:
        """
        Registra envio via MM Lite para tracking.

        Args:
            chip_id: ID do chip
            waba_id: WABA ID
            telefone: Destinatário
            template_name: Nome do template

        Returns:
            Dict com registro ou None em caso de erro
        """
        try:
            result = (
                supabase.table("meta_mm_lite_metrics")
                .insert(
                    {
                        "chip_id": chip_id,
                        "waba_id": waba_id,
                        "telefone": telefone,
                        "template_name": template_name,
                        "delivery_status": "sent",
                    }
                )
                .execute()
            )
            return result.data[0] if result.data else None

        except Exception as e:
            logger.error("Erro ao registrar envio MM Lite: %s", e)
            return None

    async def obter_metricas(
        self,
        waba_id: Optional[str] = None,
        days: int = 7,
    ) -> dict:
        """
        Obtém métricas de MM Lite.

        Args:
            waba_id: Filtrar por WABA (opcional)
            days: Período em dias

        Returns:
            Dict com total_sent, delivered, read, delivery_rate
        """
        try:
            from datetime import date, timedelta

            data_inicio = date.today() - timedelta(days=days)
            query = (
                supabase.table("meta_mm_lite_metrics")
                .select("delivery_status")
                .gte("sent_at", f"{data_inicio}T00:00:00")
            )

            if waba_id:
                query = query.eq("waba_id", waba_id)

            resp = query.execute()
            rows = resp.data or []

            total = len(rows)
            delivered = sum(1 for r in rows if r["delivery_status"] in ("delivered", "read"))
            read = sum(1 for r in rows if r["delivery_status"] == "read")

            return {
                "total_sent": total,
                "delivered": delivered,
                "read": read,
                "delivery_rate": round(delivered / total, 4) if total > 0 else 0,
                "read_rate": round(read / total, 4) if total > 0 else 0,
            }

        except Exception as e:
            logger.error("Erro ao obter métricas MM Lite: %s", e)
            return {
                "total_sent": 0,
                "delivered": 0,
                "read": 0,
                "delivery_rate": 0,
                "read_rate": 0,
            }


# Singleton
mm_lite_service = MMLiteService()
