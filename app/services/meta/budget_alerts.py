"""
Meta Budget Alerts Service.

Sprint 69 — Epic 69.3, Chunk 24.

Budget monitoring with tiered thresholds:
- 80% → warning
- 95% → critical
- 100% → block
"""

import logging
from typing import Optional
from datetime import date, timedelta

from app.core.config import settings
from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetaBudgetAlerts:
    """
    Serviço de alertas de budget Meta.

    Monitora gastos diários, semanais e mensais
    contra limites configuráveis.
    """

    THRESHOLD_WARNING = 0.80
    THRESHOLD_CRITICAL = 0.95
    THRESHOLD_BLOCK = 1.00

    async def _obter_gasto_periodo(
        self,
        data_inicio: date,
        data_fim: date,
        waba_id: Optional[str] = None,
    ) -> float:
        """Obtém gasto total em um período."""
        try:
            query = (
                supabase.table("meta_conversation_costs")
                .select("cost_usd")
                .gte("created_at", f"{data_inicio}T00:00:00")
                .lte("created_at", f"{data_fim}T23:59:59")
            )
            if waba_id:
                query = query.eq("waba_id", waba_id)

            resp = query.execute()
            rows = resp.data or []
            return sum(float(r["cost_usd"]) for r in rows)

        except Exception as e:
            logger.error("[BudgetAlerts] Erro ao obter gasto: %s", e)
            return 0.0

    def _classificar_nivel(self, percentual: float) -> str:
        """Classifica nível do alerta."""
        if percentual >= self.THRESHOLD_BLOCK:
            return "block"
        if percentual >= self.THRESHOLD_CRITICAL:
            return "critical"
        if percentual >= self.THRESHOLD_WARNING:
            return "warning"
        return "ok"

    async def verificar_budget_diario(self, waba_id: Optional[str] = None) -> dict:
        """
        Verifica budget diário.

        Args:
            waba_id: WABA ID (opcional, None = todos)

        Returns:
            Dict com limite, gasto, percentual, nivel
        """
        hoje = date.today()
        limite = settings.META_BUDGET_DIARIO_USD
        gasto = await self._obter_gasto_periodo(hoje, hoje, waba_id)
        percentual = gasto / limite if limite > 0 else 0

        return {
            "periodo": "diario",
            "limite_usd": limite,
            "gasto_usd": round(gasto, 4),
            "percentual": round(percentual, 4),
            "nivel": self._classificar_nivel(percentual),
            "data": str(hoje),
        }

    async def verificar_budget_semanal(self, waba_id: Optional[str] = None) -> dict:
        """
        Verifica budget semanal.

        Args:
            waba_id: WABA ID (opcional)

        Returns:
            Dict com limite, gasto, percentual, nivel
        """
        hoje = date.today()
        inicio_semana = hoje - timedelta(days=hoje.weekday())
        limite = settings.META_BUDGET_SEMANAL_USD
        gasto = await self._obter_gasto_periodo(inicio_semana, hoje, waba_id)
        percentual = gasto / limite if limite > 0 else 0

        return {
            "periodo": "semanal",
            "limite_usd": limite,
            "gasto_usd": round(gasto, 4),
            "percentual": round(percentual, 4),
            "nivel": self._classificar_nivel(percentual),
            "data_inicio": str(inicio_semana),
            "data_fim": str(hoje),
        }

    async def verificar_budget_mensal(self, waba_id: Optional[str] = None) -> dict:
        """
        Verifica budget mensal.

        Args:
            waba_id: WABA ID (opcional)

        Returns:
            Dict com limite, gasto, percentual, nivel
        """
        hoje = date.today()
        inicio_mes = hoje.replace(day=1)
        limite = settings.META_BUDGET_MENSAL_USD
        gasto = await self._obter_gasto_periodo(inicio_mes, hoje, waba_id)
        percentual = gasto / limite if limite > 0 else 0

        return {
            "periodo": "mensal",
            "limite_usd": limite,
            "gasto_usd": round(gasto, 4),
            "percentual": round(percentual, 4),
            "nivel": self._classificar_nivel(percentual),
            "data_inicio": str(inicio_mes),
            "data_fim": str(hoje),
        }

    async def verificar_todos_budgets(self, waba_id: Optional[str] = None) -> dict:
        """
        Verifica todos os budgets e retorna o nível mais alto de alerta.

        Args:
            waba_id: WABA ID (opcional)

        Returns:
            Dict com budgets diario, semanal, mensal e nivel_maximo
        """
        diario = await self.verificar_budget_diario(waba_id)
        semanal = await self.verificar_budget_semanal(waba_id)
        mensal = await self.verificar_budget_mensal(waba_id)

        niveis = {"ok": 0, "warning": 1, "critical": 2, "block": 3}
        nivel_max = max(
            [diario["nivel"], semanal["nivel"], mensal["nivel"]],
            key=lambda x: niveis.get(x, 0),
        )

        result = {
            "diario": diario,
            "semanal": semanal,
            "mensal": mensal,
            "nivel_maximo": nivel_max,
        }

        # Alertar via Slack se necessário
        if nivel_max in ("critical", "block"):
            await self._alertar_slack(result)

        return result

    async def _alertar_slack(self, budget_info: dict) -> None:
        """Envia alerta de budget via Slack."""
        try:
            from app.services.slack import enviar_notificacao_slack

            nivel = budget_info["nivel_maximo"]
            emoji = "🚨" if nivel == "block" else "⚠️"
            status = "BLOQUEADO" if nivel == "block" else "CRÍTICO"

            diario = budget_info["diario"]
            texto = (
                f"{emoji} *Budget Meta {status}*\n"
                f"Diário: ${diario['gasto_usd']:.2f} / ${diario['limite_usd']:.2f} "
                f"({diario['percentual']:.0%})\n"
                f"Nível: {nivel}"
            )

            await enviar_notificacao_slack(texto)

        except Exception as e:
            logger.warning("[BudgetAlerts] Erro ao alertar Slack: %s", e)


# Singleton
budget_alerts = MetaBudgetAlerts()
