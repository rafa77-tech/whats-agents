"""
Meta Dashboard Aggregation Service.

Sprint 69 — Epic 69.2, Chunk 16.

Aggregation queries for the Meta dashboard UI.
"""

import logging
from typing import Optional, List
from datetime import date, timedelta

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetaDashboardService:
    """
    Serviço de agregação para dashboard Meta.

    Fornece dados consolidados para a UI do dashboard.
    """

    async def obter_quality_overview(self) -> dict:
        """
        Obtém overview de qualidade de todos os chips Meta.

        Returns:
            Dict com contadores por rating (GREEN, YELLOW, RED)
        """
        try:
            result = (
                supabase.table("chips")
                .select("id, nome, status, meta_waba_id, meta_quality_rating, trust_score")
                .not_.is_("meta_waba_id", "null")
                .execute()
            )
            chips = result.data or []

            overview = {
                "total": len(chips),
                "green": 0,
                "yellow": 0,
                "red": 0,
                "unknown": 0,
                "chips": [],
            }

            for chip in chips:
                rating = (chip.get("meta_quality_rating") or "UNKNOWN").upper()
                if rating == "GREEN":
                    overview["green"] += 1
                elif rating == "YELLOW":
                    overview["yellow"] += 1
                elif rating == "RED":
                    overview["red"] += 1
                else:
                    overview["unknown"] += 1

                overview["chips"].append(
                    {
                        "id": chip["id"],
                        "nome": chip.get("nome"),
                        "status": chip.get("status"),
                        "quality_rating": rating,
                        "trust_score": chip.get("trust_score", 0),
                    }
                )

            return overview

        except Exception as e:
            logger.error("[MetaDashboard] Erro ao obter quality overview: %s", e)
            return {"total": 0, "green": 0, "yellow": 0, "red": 0, "unknown": 0, "chips": []}

    async def obter_quality_history(
        self,
        chip_id: Optional[str] = None,
        days: int = 30,
    ) -> List[dict]:
        """
        Obtém histórico de qualidade por chip.

        Args:
            chip_id: Filtrar por chip
            days: Período em dias

        Returns:
            Lista de registros de qualidade
        """
        try:
            data_inicio = date.today() - timedelta(days=days)
            query = (
                supabase.table("meta_quality_history")
                .select("*")
                .gte("created_at", f"{data_inicio}T00:00:00")
                .order("created_at", desc=True)
                .limit(500)
            )

            if chip_id:
                query = query.eq("chip_id", chip_id)

            result = query.execute()
            return result.data or []

        except Exception as e:
            logger.error("[MetaDashboard] Erro ao obter quality history: %s", e)
            return []

    async def obter_cost_summary(
        self,
        days: int = 7,
    ) -> dict:
        """
        Obtém resumo de custos.

        Args:
            days: Período em dias

        Returns:
            Dict com total, free_pct, by_category
        """
        try:
            data_inicio = date.today() - timedelta(days=days)
            result = (
                supabase.table("meta_conversation_costs")
                .select("message_category, cost_usd, is_free")
                .gte("created_at", f"{data_inicio}T00:00:00")
                .execute()
            )
            rows = result.data or []

            total_cost = sum(float(r["cost_usd"]) for r in rows)
            total_msgs = len(rows)
            free_msgs = sum(1 for r in rows if r["is_free"])

            by_category = {}
            for row in rows:
                cat = row["message_category"]
                if cat not in by_category:
                    by_category[cat] = {"count": 0, "cost_usd": 0.0}
                by_category[cat]["count"] += 1
                by_category[cat]["cost_usd"] += float(row["cost_usd"])

            # Arredondar
            for cat in by_category:
                by_category[cat]["cost_usd"] = round(by_category[cat]["cost_usd"], 4)

            return {
                "total_cost_usd": round(total_cost, 4),
                "total_messages": total_msgs,
                "free_messages": free_msgs,
                "free_pct": round(free_msgs / total_msgs, 4) if total_msgs > 0 else 0,
                "by_category": by_category,
                "period_days": days,
            }

        except Exception as e:
            logger.error("[MetaDashboard] Erro ao obter cost summary: %s", e)
            return {
                "total_cost_usd": 0,
                "total_messages": 0,
                "free_messages": 0,
                "free_pct": 0,
                "by_category": {},
                "period_days": days,
            }

    async def obter_cost_by_chip(self, days: int = 7) -> List[dict]:
        """
        Obtém custo por chip.

        Args:
            days: Período em dias

        Returns:
            Lista de chips com custos
        """
        try:
            data_inicio = date.today() - timedelta(days=days)
            result = (
                supabase.table("meta_conversation_costs")
                .select("chip_id, cost_usd")
                .gte("created_at", f"{data_inicio}T00:00:00")
                .execute()
            )
            rows = result.data or []

            chips = {}
            for row in rows:
                cid = row["chip_id"]
                if cid not in chips:
                    chips[cid] = {"chip_id": cid, "total_messages": 0, "total_cost_usd": 0.0}
                chips[cid]["total_messages"] += 1
                chips[cid]["total_cost_usd"] += float(row["cost_usd"])

            for cid in chips:
                chips[cid]["total_cost_usd"] = round(chips[cid]["total_cost_usd"], 4)

            return sorted(chips.values(), key=lambda x: x["total_cost_usd"], reverse=True)

        except Exception as e:
            logger.error("[MetaDashboard] Erro ao obter cost by chip: %s", e)
            return []

    async def obter_cost_by_template(self, days: int = 7) -> List[dict]:
        """
        Obtém custo por template.

        Args:
            days: Período em dias

        Returns:
            Lista de templates com custos
        """
        try:
            data_inicio = date.today() - timedelta(days=days)
            result = (
                supabase.table("meta_conversation_costs")
                .select("template_name, cost_usd")
                .gte("created_at", f"{data_inicio}T00:00:00")
                .not_.is_("template_name", "null")
                .execute()
            )
            rows = result.data or []

            templates = {}
            for row in rows:
                tname = row["template_name"]
                if tname not in templates:
                    templates[tname] = {
                        "template_name": tname,
                        "total_sent": 0,
                        "total_cost_usd": 0.0,
                    }
                templates[tname]["total_sent"] += 1
                templates[tname]["total_cost_usd"] += float(row["cost_usd"])

            for tname in templates:
                templates[tname]["total_cost_usd"] = round(
                    templates[tname]["total_cost_usd"], 4
                )

            return sorted(templates.values(), key=lambda x: x["total_cost_usd"], reverse=True)

        except Exception as e:
            logger.error("[MetaDashboard] Erro ao obter cost by template: %s", e)
            return []

    async def obter_templates_com_analytics(
        self,
        waba_id: Optional[str] = None,
    ) -> List[dict]:
        """
        Lista templates com analytics joinados.

        Args:
            waba_id: Filtrar por WABA

        Returns:
            Lista de templates com métricas
        """
        try:
            query = supabase.table("meta_templates").select("*")
            if waba_id:
                query = query.eq("waba_id", waba_id)

            result = query.order("created_at", desc=True).execute()
            templates = result.data or []

            # Join com analytics (últimos 7 dias)
            for template in templates:
                try:
                    analytics_resp = (
                        supabase.table("meta_template_analytics")
                        .select("sent, delivered, read, delivery_rate, read_rate")
                        .eq("template_name", template["template_name"])
                        .order("date", desc=True)
                        .limit(1)
                        .execute()
                    )
                    if analytics_resp.data:
                        template["analytics"] = analytics_resp.data[0]
                    else:
                        template["analytics"] = None
                except Exception:
                    template["analytics"] = None

            return templates

        except Exception as e:
            logger.error("[MetaDashboard] Erro ao obter templates com analytics: %s", e)
            return []


# Singleton
dashboard_service = MetaDashboardService()
