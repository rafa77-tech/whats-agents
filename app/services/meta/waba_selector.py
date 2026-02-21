"""
Multi-WABA Strategy Selector.

Sprint 70+ — Chunk 29.

v1: Single WABA passthrough with interface ready for multi-WABA.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class WabaSelection:
    """Resultado de seleção de WABA."""

    waba_id: str
    reason: str
    risk_level: str = "low"  # low, medium, high


class WabaSelector:
    """
    Seletor de WABA para envio de mensagens.

    v1: Passthrough — usa a primeira WABA disponível.
    Interface pronta para multi-WABA em versões futuras.

    Regras futuras:
    - Discovery → WABA-A (lower risk)
    - Offer → WABA-B (higher trust)
    - Support → WABA-C
    """

    async def selecionar_waba(
        self,
        intent: str = "default",
        medico_context: Optional[dict] = None,
    ) -> Optional[WabaSelection]:
        """
        Seleciona WABA ideal para o contexto.

        Args:
            intent: Intenção (discovery, offer, support, campaign)
            medico_context: Contexto do médico (histórico, interações)

        Returns:
            WabaSelection ou None
        """
        try:
            # v1: buscar primeira WABA ativa
            result = (
                supabase.table("chips")
                .select("meta_waba_id, status, meta_quality_rating, trust_score")
                .not_.is_("meta_waba_id", "null")
                .eq("status", "active")
                .order("trust_score", desc=True)
                .limit(1)
                .execute()
            )

            if not result.data:
                logger.warning("[WabaSelector] Nenhuma WABA ativa encontrada")
                return None

            chip = result.data[0]
            waba_id = chip["meta_waba_id"]

            # v1: Passthrough com risk level baseado no intent
            risk_map = {
                "discovery": "medium",
                "offer": "low",
                "support": "low",
                "campaign": "medium",
                "default": "low",
            }

            return WabaSelection(
                waba_id=waba_id,
                reason=f"v1 passthrough — intent: {intent}",
                risk_level=risk_map.get(intent, "low"),
            )

        except Exception as e:
            logger.error("[WabaSelector] Erro ao selecionar WABA: %s", e)
            return None

    async def listar_wabas_disponiveis(self) -> list:
        """
        Lista WABAs disponíveis com status.

        Returns:
            Lista de WABAs
        """
        try:
            result = (
                supabase.table("chips")
                .select("meta_waba_id, nome, status, meta_quality_rating, trust_score")
                .not_.is_("meta_waba_id", "null")
                .execute()
            )

            # Agrupar por WABA (pode ter múltiplos chips por WABA)
            wabas = {}
            for chip in result.data or []:
                waba_id = chip["meta_waba_id"]
                if waba_id not in wabas:
                    wabas[waba_id] = {
                        "waba_id": waba_id,
                        "chips": [],
                        "active_chips": 0,
                    }
                wabas[waba_id]["chips"].append(chip)
                if chip["status"] == "active":
                    wabas[waba_id]["active_chips"] += 1

            return list(wabas.values())

        except Exception as e:
            logger.error("[WabaSelector] Erro ao listar WABAs: %s", e)
            return []


# Singleton
waba_selector = WabaSelector()
