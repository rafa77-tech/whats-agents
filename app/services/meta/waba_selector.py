"""
Multi-WABA Strategy Selector.

Sprint 70+ — Chunk 29.
Sprint 72: v2 — selecao por quality, custo e capacidade.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class WabaSelection:
    """Resultado de seleção de WABA."""

    waba_id: str
    reason: str
    risk_level: str = "low"  # low, medium, high


@dataclass
class WabaStats:
    """Estatísticas de uma WABA."""

    waba_id: str
    chip_count: int
    active_chips: int
    avg_trust: float
    min_quality: str  # GREEN, YELLOW, RED
    has_red: bool


class WabaSelector:
    """
    Seletor de WABA para envio de mensagens.

    v2: Selecao inteligente por quality, trust e intent.

    Estrategia:
    - Discovery/Campaign → WABA com maior trust medio (protege reputation)
    - Offer/Support → WABA com mais chips ativos (capacidade)
    - Evita WABAs com quality RED
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
            wabas = await self._agregar_wabas()

            if not wabas:
                logger.warning("[WabaSelector] Nenhuma WABA ativa encontrada")
                return None

            # Se medico ja tem historico com uma WABA, preferir ela
            if medico_context and medico_context.get("telefone"):
                waba_historico = await self._buscar_waba_historico(
                    medico_context["telefone"], wabas
                )
                if waba_historico:
                    return WabaSelection(
                        waba_id=waba_historico.waba_id,
                        reason=f"afinidade medico — intent: {intent}",
                        risk_level="low",
                    )

            # Filtrar WABAs sem chips RED (para discovery/campaign)
            wabas_safe = [w for w in wabas if not w.has_red]
            pool = wabas_safe if wabas_safe else wabas

            # Selecionar baseado no intent
            if intent in ("discovery", "campaign"):
                # Maior trust = menor risco de ban
                selected = max(pool, key=lambda w: w.avg_trust)
                reason = f"maior trust ({selected.avg_trust:.0f}) — intent: {intent}"
            else:
                # Maior capacidade
                selected = max(pool, key=lambda w: w.active_chips)
                reason = f"maior capacidade ({selected.active_chips} chips) — intent: {intent}"

            risk_map = {
                "discovery": "medium",
                "offer": "low",
                "support": "low",
                "campaign": "medium",
                "default": "low",
            }

            return WabaSelection(
                waba_id=selected.waba_id,
                reason=reason,
                risk_level=risk_map.get(intent, "low"),
            )

        except Exception as e:
            logger.error("[WabaSelector] Erro ao selecionar WABA: %s", e)
            return None

    async def _agregar_wabas(self) -> List[WabaStats]:
        """Agrega estatísticas por WABA a partir dos chips."""
        result = (
            supabase.table("chips")
            .select("meta_waba_id, status, meta_quality_rating, trust_score")
            .not_.is_("meta_waba_id", "null")
            .execute()
        )

        wabas: dict = {}
        for chip in result.data or []:
            waba_id = chip["meta_waba_id"]
            if waba_id not in wabas:
                wabas[waba_id] = {
                    "chips": [],
                    "active": 0,
                    "trusts": [],
                    "has_red": False,
                }
            w = wabas[waba_id]
            w["chips"].append(chip)
            if chip["status"] == "active":
                w["active"] += 1
                w["trusts"].append(chip.get("trust_score", 0))
            if chip.get("meta_quality_rating") == "RED":
                w["has_red"] = True

        stats = []
        for waba_id, w in wabas.items():
            if w["active"] == 0:
                continue
            avg_trust = sum(w["trusts"]) / len(w["trusts"]) if w["trusts"] else 0
            min_q = "GREEN"
            for c in w["chips"]:
                q = c.get("meta_quality_rating", "GREEN")
                if q == "RED":
                    min_q = "RED"
                elif q == "YELLOW" and min_q != "RED":
                    min_q = "YELLOW"
            stats.append(
                WabaStats(
                    waba_id=waba_id,
                    chip_count=len(w["chips"]),
                    active_chips=w["active"],
                    avg_trust=avg_trust,
                    min_quality=min_q,
                    has_red=w["has_red"],
                )
            )

        return stats

    async def _buscar_waba_historico(
        self, telefone: str, wabas: List[WabaStats]
    ) -> Optional[WabaStats]:
        """Busca WABA que já interagiu com este telefone."""
        try:
            result = (
                supabase.table("chip_interactions")
                .select("chip_id, chips!inner(meta_waba_id)")
                .eq("destinatario", telefone)
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )

            if result.data:
                chip_data = result.data[0].get("chips", {})
                waba_id = chip_data.get("meta_waba_id") if chip_data else None
                if waba_id:
                    for w in wabas:
                        if w.waba_id == waba_id:
                            return w
        except Exception as e:
            logger.debug("[WabaSelector] Erro ao buscar historico WABA: %s", e)

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
