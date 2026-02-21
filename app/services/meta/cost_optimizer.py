"""
Meta Cost Optimization Engine.

Sprint 69 — Epic 69.3, Chunk 23.

Decision engine for optimal message sending:
- Within window (FREE) > Utility template > Marketing template
- Campaign cost estimation and optimization suggestions.
"""

import logging
from typing import Optional, List
from dataclasses import dataclass, field

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class SendDecision:
    """Decisão de envio com tipo, template e custo estimado."""

    method: str  # "free_window", "utility_template", "marketing_template", "mm_lite"
    template_name: Optional[str] = None
    estimated_cost: float = 0.0
    reason: str = ""


@dataclass
class CostEstimate:
    """Estimativa de custo de uma campanha."""

    total: float = 0.0
    by_category: dict = field(default_factory=dict)
    recipients_in_window: int = 0
    recipients_outside: int = 0


class MetaCostOptimizer:
    """
    Motor de otimização de custos Meta.

    Decide o tipo de envio mais econômico e estima custos de campanhas.
    Prioridade: free window > utility > marketing.
    """

    async def decidir_tipo_envio(
        self,
        chip_id: str,
        telefone: str,
        intent: str = "marketing",
    ) -> SendDecision:
        """
        Decide o melhor tipo de envio para um destinatário.

        Priority:
        1. Within 24h window → FREE (service message)
        2. Utility template (if applicable) → lower cost
        3. Marketing template → standard cost
        4. MM Lite (if enabled and campaign) → Meta-optimized

        Args:
            chip_id: ID do chip
            telefone: Destinatário
            intent: Intenção (marketing, utility, confirmation, followup)

        Returns:
            SendDecision com recomendação
        """
        # Verificar se está na janela de conversa
        try:
            from app.services.meta.window_tracker import window_tracker

            in_window = await window_tracker.esta_na_janela(chip_id, telefone)
        except Exception:
            in_window = False

        if in_window:
            return SendDecision(
                method="free_window",
                template_name=None,
                estimated_cost=0.0,
                reason="Dentro da janela de conversa — mensagem gratuita",
            )

        # Fora da janela: precisa de template
        if intent in ("utility", "confirmation", "update", "followup"):
            return SendDecision(
                method="utility_template",
                template_name=None,
                estimated_cost=settings.META_PRICING_UTILITY_USD,
                reason=f"Template utility para intent '{intent}'",
            )

        # Marketing
        if settings.META_MM_LITE_ENABLED:
            return SendDecision(
                method="mm_lite",
                template_name=None,
                estimated_cost=settings.META_PRICING_MARKETING_USD,
                reason="MM Lite habilitado para marketing",
            )

        return SendDecision(
            method="marketing_template",
            template_name=None,
            estimated_cost=settings.META_PRICING_MARKETING_USD,
            reason="Template marketing padrão",
        )

    async def estimar_custo_campanha(self, campanha_id: str) -> CostEstimate:
        """
        Estima custo de uma campanha antes de executar.

        Args:
            campanha_id: ID da campanha

        Returns:
            CostEstimate com total e breakdown
        """
        try:
            # Buscar envios da campanha
            envios_resp = (
                supabase.table("envios")
                .select("telefone, chip_id, status")
                .eq("campanha_id", campanha_id)
                .eq("status", "pendente")
                .execute()
            )
            envios = envios_resp.data or []

            if not envios:
                return CostEstimate()

            in_window = 0
            outside_window = 0
            total_cost = 0.0

            for envio in envios:
                try:
                    from app.services.meta.window_tracker import window_tracker

                    is_in = await window_tracker.esta_na_janela(
                        envio.get("chip_id", ""),
                        envio.get("telefone", ""),
                    )
                except Exception:
                    is_in = False

                if is_in:
                    in_window += 1
                else:
                    outside_window += 1
                    total_cost += settings.META_PRICING_MARKETING_USD

            return CostEstimate(
                total=round(total_cost, 4),
                by_category={
                    "service": {"count": in_window, "cost": 0.0},
                    "marketing": {
                        "count": outside_window,
                        "cost": round(outside_window * settings.META_PRICING_MARKETING_USD, 4),
                    },
                },
                recipients_in_window=in_window,
                recipients_outside=outside_window,
            )

        except Exception as e:
            logger.error("[CostOptimizer] Erro ao estimar campanha %s: %s", campanha_id, e)
            return CostEstimate()

    async def sugerir_otimizacao(self, campanha_id: str) -> List[dict]:
        """
        Sugere otimizações para reduzir custo de campanha.

        Args:
            campanha_id: ID da campanha

        Returns:
            Lista de sugestões
        """
        sugestoes = []

        estimate = await self.estimar_custo_campanha(campanha_id)

        total_recipients = estimate.recipients_in_window + estimate.recipients_outside

        if total_recipients == 0:
            return [{"tipo": "info", "mensagem": "Nenhum envio pendente na campanha"}]

        # Sugestão 1: agendar para horário com mais janelas abertas
        if estimate.recipients_outside > estimate.recipients_in_window:
            pct_fora = estimate.recipients_outside / total_recipients * 100
            sugestoes.append(
                {
                    "tipo": "schedule",
                    "mensagem": (
                        f"{pct_fora:.0f}% dos destinatários estão fora da janela. "
                        "Considere enviar durante o horário comercial para capturar "
                        "mais janelas abertas."
                    ),
                    "economia_estimada": round(
                        estimate.recipients_outside * settings.META_PRICING_MARKETING_USD * 0.3,
                        2,
                    ),
                }
            )

        # Sugestão 2: usar utility template quando possível
        if estimate.by_category.get("marketing", {}).get("count", 0) > 0:
            sugestoes.append(
                {
                    "tipo": "template_type",
                    "mensagem": (
                        "Considere usar templates UTILITY para mensagens de confirmação "
                        "ou atualização. Utility custa "
                        f"${settings.META_PRICING_UTILITY_USD} vs "
                        f"${settings.META_PRICING_MARKETING_USD} (marketing)."
                    ),
                    "economia_estimada": round(
                        estimate.by_category["marketing"]["count"]
                        * (settings.META_PRICING_MARKETING_USD - settings.META_PRICING_UTILITY_USD),
                        2,
                    ),
                }
            )

        # Sugestão 3: MM Lite
        if not settings.META_MM_LITE_ENABLED and estimate.recipients_outside > 10:
            sugestoes.append(
                {
                    "tipo": "mm_lite",
                    "mensagem": (
                        "Habilitar MM Lite pode aumentar delivery rate em ~9% sem custo adicional."
                    ),
                    "economia_estimada": 0,
                }
            )

        if not sugestoes:
            sugestoes.append(
                {
                    "tipo": "ok",
                    "mensagem": "Campanha já está otimizada para custos.",
                    "economia_estimada": 0,
                }
            )

        return sugestoes


# Singleton
cost_optimizer = MetaCostOptimizer()
