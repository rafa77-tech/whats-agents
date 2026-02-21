"""
Conversation Analytics para Meta WhatsApp Business API.

Sprint 67 (Epic 67.4, Chunk 6b).

Tracking de custos por mensagem Meta:
- Registra custo de cada mensagem enviada
- Determina categoria (marketing, utility, authentication, service)
- Budget diário com alertas
"""

import logging
from datetime import date
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)

# Pricing map por categoria
PRICING_MAP = {
    "marketing": settings.META_PRICING_MARKETING_USD,
    "utility": settings.META_PRICING_UTILITY_USD,
    "authentication": settings.META_PRICING_AUTHENTICATION_USD,
    "service": 0.0,  # Mensagens dentro da janela são gratuitas
}


class MetaConversationAnalytics:
    """
    Tracking de custos de conversas Meta.

    - Registra custo por mensagem
    - Determina categoria com base na janela de conversa
    - Verifica budget diário e alerta quando próximo do limite
    """

    async def registrar_custo_mensagem(
        self,
        chip_id: str,
        waba_id: str,
        telefone: str,
        template_name: Optional[str] = None,
        is_within_window: bool = False,
        message_category: Optional[str] = None,
    ) -> dict:
        """
        Registra custo de uma mensagem enviada.

        Args:
            chip_id: ID do chip que enviou
            waba_id: WABA ID
            telefone: Destinatário
            template_name: Nome do template (se usado)
            is_within_window: Se está dentro da janela 24h
            message_category: Categoria forçada (se não fornecida, auto-detecta)

        Returns:
            Dict com category, cost_usd, is_free.
        """
        category = message_category or self._determinar_categoria(
            template_name=template_name,
            is_within_window=is_within_window,
        )

        is_free = category == "service"
        cost_usd = 0.0 if is_free else PRICING_MAP.get(category, 0.0)

        try:
            supabase.table("meta_conversation_costs").insert(
                {
                    "chip_id": chip_id,
                    "waba_id": waba_id,
                    "telefone": telefone,
                    "message_category": category,
                    "is_free": is_free,
                    "cost_usd": cost_usd,
                    "template_name": template_name,
                }
            ).execute()

        except Exception as e:
            logger.error("Erro ao registrar custo mensagem: %s", e)

        return {
            "category": category,
            "cost_usd": cost_usd,
            "is_free": is_free,
        }

    def _determinar_categoria(
        self,
        template_name: Optional[str] = None,
        is_within_window: bool = False,
    ) -> str:
        """
        Determina categoria da mensagem.

        - Dentro da janela (sem template): service (grátis)
        - Template com "auth" no nome: authentication
        - Template com "utility" no nome: utility
        - Outros templates: marketing (padrão para campanhas)
        """
        if is_within_window and not template_name:
            return "service"

        if template_name:
            name_lower = template_name.lower()
            if "auth" in name_lower or "otp" in name_lower or "verification" in name_lower:
                return "authentication"
            if "utility" in name_lower or "confirmation" in name_lower or "update" in name_lower:
                return "utility"
            # Default para templates: marketing
            return "marketing"

        # Fora da janela sem template (não deveria chegar aqui)
        return "marketing"

    async def obter_custo_periodo(
        self,
        data_inicio: Optional[date] = None,
        data_fim: Optional[date] = None,
        waba_id: Optional[str] = None,
    ) -> dict:
        """
        Obtém custo total em um período.

        Returns:
            Dict com total_messages, total_cost_usd, free_messages, por_categoria.
        """
        try:
            data_inicio = data_inicio or date.today()
            data_fim = data_fim or date.today()

            query = (
                supabase.table("meta_conversation_costs")
                .select("message_category, cost_usd, is_free")
                .gte("created_at", f"{data_inicio}T00:00:00")
                .lte("created_at", f"{data_fim}T23:59:59")
            )

            if waba_id:
                query = query.eq("waba_id", waba_id)

            resp = query.execute()
            rows = resp.data or []

            total_cost = sum(float(r["cost_usd"]) for r in rows)
            free_count = sum(1 for r in rows if r["is_free"])

            # Agrupar por categoria
            por_categoria = {}
            for row in rows:
                cat = row["message_category"]
                if cat not in por_categoria:
                    por_categoria[cat] = {"count": 0, "cost_usd": 0.0}
                por_categoria[cat]["count"] += 1
                por_categoria[cat]["cost_usd"] += float(row["cost_usd"])

            return {
                "total_messages": len(rows),
                "total_cost_usd": round(total_cost, 4),
                "free_messages": free_count,
                "por_categoria": por_categoria,
            }

        except Exception as e:
            logger.error("Erro ao obter custo período: %s", e)
            return {
                "total_messages": 0,
                "total_cost_usd": 0,
                "free_messages": 0,
                "por_categoria": {},
            }

    async def obter_custo_por_chip(
        self,
        data: Optional[date] = None,
    ) -> list:
        """Obtém custo por chip no dia."""
        try:
            data = data or date.today()
            query = (
                supabase.table("meta_conversation_costs")
                .select("chip_id, message_category, cost_usd, is_free")
                .gte("created_at", f"{data}T00:00:00")
                .lte("created_at", f"{data}T23:59:59")
            )

            resp = query.execute()
            rows = resp.data or []

            # Agrupar por chip
            chips = {}
            for row in rows:
                cid = row["chip_id"]
                if cid not in chips:
                    chips[cid] = {"chip_id": cid, "total_messages": 0, "total_cost_usd": 0.0}
                chips[cid]["total_messages"] += 1
                chips[cid]["total_cost_usd"] += float(row["cost_usd"])

            return list(chips.values())

        except Exception as e:
            logger.error("Erro ao obter custo por chip: %s", e)
            return []

    async def verificar_budget(self) -> dict:
        """
        Verifica se o budget diário está sendo respeitado.

        Returns:
            Dict com budget_diario, gasto_hoje, percentual, alerta.
        """
        custos = await self.obter_custo_periodo()
        budget = settings.META_BUDGET_DIARIO_USD
        threshold = settings.META_BUDGET_ALERT_THRESHOLD

        gasto = custos["total_cost_usd"]
        percentual = gasto / budget if budget > 0 else 0

        return {
            "budget_diario_usd": budget,
            "gasto_hoje_usd": gasto,
            "percentual": round(percentual, 4),
            "alerta": percentual >= threshold,
            "excedido": percentual >= 1.0,
            "total_messages": custos["total_messages"],
        }

    async def alertar_budget_excedido(self) -> Optional[dict]:
        """
        Verifica budget e alerta via Slack se necessário.

        Returns:
            Dict com info do alerta, ou None se tudo OK.
        """
        budget_info = await self.verificar_budget()

        if not budget_info["alerta"]:
            return None

        try:
            from app.services.slack import enviar_notificacao_slack

            if budget_info["excedido"]:
                emoji = "🚨"
                status = "EXCEDIDO"
            else:
                emoji = "⚠️"
                status = "PRÓXIMO DO LIMITE"

            texto = (
                f"{emoji} *Budget Meta {status}*\n"
                f"Gasto hoje: ${budget_info['gasto_hoje_usd']:.2f} / "
                f"${budget_info['budget_diario_usd']:.2f} "
                f"({budget_info['percentual']:.0%})\n"
                f"Mensagens: {budget_info['total_messages']}"
            )

            await enviar_notificacao_slack(texto)

        except Exception as e:
            logger.warning("Erro ao alertar budget Slack: %s", e)

        return budget_info


# Singleton
conversation_analytics = MetaConversationAnalytics()
