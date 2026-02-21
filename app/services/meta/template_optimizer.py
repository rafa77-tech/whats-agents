"""
Template Auto-Optimization.

Sprint 70+ — Chunk 28.

Rule-based heuristics for template performance analysis:
- Delivery < 80% → suggestions
- Read < 30% → suggestions
"""

import logging
from typing import List, Optional

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class MetaTemplateOptimizer:
    """
    Otimizador automático de templates.

    v1: Heurísticas baseadas em regras para identificar
    templates de baixa performance e sugerir melhorias.
    """

    THRESHOLD_DELIVERY = 0.80
    THRESHOLD_READ = 0.30
    MIN_SENT = 10  # Mínimo de envios para análise

    async def identificar_baixa_performance(
        self,
        waba_id: Optional[str] = None,
        days: int = 7,
    ) -> List[dict]:
        """
        Identifica templates com baixa performance.

        Args:
            waba_id: Filtrar por WABA
            days: Período de análise

        Returns:
            Lista de templates com problemas
        """
        try:
            from datetime import date, timedelta

            data_inicio = date.today() - timedelta(days=days)
            query = (
                supabase.table("meta_template_analytics")
                .select("template_name, waba_id, sent, delivered, read, delivery_rate, read_rate")
                .gte("date", str(data_inicio))
            )

            if waba_id:
                query = query.eq("waba_id", waba_id)

            result = query.execute()
            rows = result.data or []

            # Agregar por template
            templates = {}
            for row in rows:
                name = row["template_name"]
                if name not in templates:
                    templates[name] = {
                        "template_name": name,
                        "waba_id": row["waba_id"],
                        "total_sent": 0,
                        "total_delivered": 0,
                        "total_read": 0,
                    }
                templates[name]["total_sent"] += row.get("sent", 0) or 0
                templates[name]["total_delivered"] += row.get("delivered", 0) or 0
                templates[name]["total_read"] += row.get("read", 0) or 0

            problemas = []
            for t in templates.values():
                if t["total_sent"] < self.MIN_SENT:
                    continue

                delivery_rate = t["total_delivered"] / t["total_sent"]
                read_rate = t["total_read"] / t["total_sent"]

                issues = []
                if delivery_rate < self.THRESHOLD_DELIVERY:
                    issues.append(f"Delivery rate baixo: {delivery_rate:.0%}")
                if read_rate < self.THRESHOLD_READ:
                    issues.append(f"Read rate baixo: {read_rate:.0%}")

                if issues:
                    problemas.append(
                        {
                            **t,
                            "delivery_rate": round(delivery_rate, 4),
                            "read_rate": round(read_rate, 4),
                            "issues": issues,
                        }
                    )

            return problemas

        except Exception as e:
            logger.error("[TemplateOptimizer] Erro ao identificar baixa performance: %s", e)
            return []

    async def sugerir_melhorias(self, template_name: str) -> List[dict]:
        """
        Sugere melhorias para um template específico.

        Args:
            template_name: Nome do template

        Returns:
            Lista de sugestões
        """
        sugestoes = []

        try:
            # Buscar analytics recente
            result = (
                supabase.table("meta_template_analytics")
                .select("sent, delivered, read, delivery_rate, read_rate")
                .eq("template_name", template_name)
                .order("date", desc=True)
                .limit(7)
                .execute()
            )
            rows = result.data or []

            if not rows:
                return [{"tipo": "info", "mensagem": "Sem dados de analytics disponíveis"}]

            total_sent = sum(r.get("sent", 0) or 0 for r in rows)
            total_delivered = sum(r.get("delivered", 0) or 0 for r in rows)
            total_read = sum(r.get("read", 0) or 0 for r in rows)

            if total_sent < self.MIN_SENT:
                return [
                    {
                        "tipo": "info",
                        "mensagem": f"Poucos envios ({total_sent}). Aguarde mais dados.",
                    }
                ]

            delivery_rate = total_delivered / total_sent
            read_rate = total_read / total_sent

            if delivery_rate < self.THRESHOLD_DELIVERY:
                sugestoes.append(
                    {
                        "tipo": "delivery",
                        "mensagem": (
                            f"Delivery rate ({delivery_rate:.0%}) abaixo de {self.THRESHOLD_DELIVERY:.0%}. "
                            "Considere: verificar quality rating do chip, "
                            "reduzir frequência de envio, ou revisar conteúdo."
                        ),
                        "prioridade": "alta",
                    }
                )

            if read_rate < self.THRESHOLD_READ:
                sugestoes.append(
                    {
                        "tipo": "read_rate",
                        "mensagem": (
                            f"Read rate ({read_rate:.0%}) abaixo de {self.THRESHOLD_READ:.0%}. "
                            "Considere: mensagem mais curta, CTA mais claro, "
                            "ou enviar em horário diferente."
                        ),
                        "prioridade": "media",
                    }
                )

            if not sugestoes:
                sugestoes.append(
                    {
                        "tipo": "ok",
                        "mensagem": "Template com performance dentro do esperado.",
                        "prioridade": "baixa",
                    }
                )

            return sugestoes

        except Exception as e:
            logger.error("[TemplateOptimizer] Erro ao sugerir melhorias: %s", e)
            return [{"tipo": "error", "mensagem": str(e)}]

    async def comparar_variantes_ab(
        self,
        template_a: str,
        template_b: str,
        days: int = 7,
    ) -> dict:
        """
        Compara performance de duas variantes de template.

        Args:
            template_a: Nome do template A
            template_b: Nome do template B
            days: Período de comparação

        Returns:
            Dict com comparação
        """
        try:
            from datetime import date, timedelta

            data_inicio = date.today() - timedelta(days=days)

            async def _obter_stats(name):
                result = (
                    supabase.table("meta_template_analytics")
                    .select("sent, delivered, read")
                    .eq("template_name", name)
                    .gte("date", str(data_inicio))
                    .execute()
                )
                rows = result.data or []
                sent = sum(r.get("sent", 0) or 0 for r in rows)
                delivered = sum(r.get("delivered", 0) or 0 for r in rows)
                read = sum(r.get("read", 0) or 0 for r in rows)
                return {
                    "template_name": name,
                    "sent": sent,
                    "delivered": delivered,
                    "read": read,
                    "delivery_rate": round(delivered / sent, 4) if sent > 0 else 0,
                    "read_rate": round(read / sent, 4) if sent > 0 else 0,
                }

            stats_a = await _obter_stats(template_a)
            stats_b = await _obter_stats(template_b)

            winner = None
            if stats_a["delivery_rate"] > stats_b["delivery_rate"]:
                winner = template_a
            elif stats_b["delivery_rate"] > stats_a["delivery_rate"]:
                winner = template_b

            return {
                "template_a": stats_a,
                "template_b": stats_b,
                "winner": winner,
                "period_days": days,
            }

        except Exception as e:
            logger.error("[TemplateOptimizer] Erro ao comparar A/B: %s", e)
            return {"template_a": {}, "template_b": {}, "winner": None}


# Singleton
template_optimizer = MetaTemplateOptimizer()
