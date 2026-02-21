"""
Template Analytics para Meta WhatsApp Business API.

Sprint 67 (Epic 67.3, Chunk 6a).

Coleta e analisa métricas de performance de templates:
- Sent, delivered, read, clicked, failed counts
- Delivery rate e read rate (computados pelo banco)
- Ranking de templates e detecção de baixa performance
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from app.core.config import settings
from app.services.supabase import supabase
from app.services.http_client import get_http_client

logger = logging.getLogger(__name__)

# Thresholds de performance
THRESHOLD_DELIVERY_RATE = 0.80  # < 80% delivery = baixa performance
THRESHOLD_READ_RATE = 0.30  # < 30% read = baixa performance
MIN_SENT_FOR_ANALYSIS = 10  # Mínimo de envios para considerar na análise


class MetaTemplateAnalytics:
    """
    Coleta e analisa métricas de templates Meta.

    - Poll diário de analytics via Graph API
    - Salva em meta_template_analytics (upsert por waba_id/template/language/date)
    - Ranking de templates por delivery/read rate
    - Detecção de templates com baixa performance
    """

    def __init__(self):
        self.api_version = settings.META_GRAPH_API_VERSION

    async def coletar_analytics(self) -> dict:
        """
        Coleta analytics de todos os templates ativos de todas as WABAs.

        Returns:
            Dict com resumo: total_wabas, templates_atualizados, erros.
        """
        resultado = {
            "total_wabas": 0,
            "templates_atualizados": 0,
            "erros": 0,
        }

        try:
            # Buscar WABAs distintas com chips ativos
            resp = (
                supabase.table("chips")
                .select("meta_waba_id, meta_access_token")
                .eq("provider", "meta")
                .in_("status", ["active", "warming", "ready"])
                .not_.is_("meta_waba_id", "null")
                .execute()
            )

            # Agrupar por WABA (pegar primeiro token disponível)
            wabas = {}
            for chip in resp.data or []:
                waba_id = chip["meta_waba_id"]
                if waba_id and waba_id not in wabas and chip.get("meta_access_token"):
                    wabas[waba_id] = chip["meta_access_token"]

            resultado["total_wabas"] = len(wabas)

            for waba_id, token in wabas.items():
                try:
                    analytics = await self._consultar_analytics_api(waba_id, token)
                    if analytics:
                        count = await self._salvar_analytics(waba_id, analytics)
                        resultado["templates_atualizados"] += count
                except Exception as e:
                    resultado["erros"] += 1
                    logger.error("Erro ao coletar analytics WABA %s: %s", waba_id, e)

        except Exception as e:
            resultado["erros"] += 1
            logger.error("Erro ao listar WABAs para analytics: %s", e)

        logger.info(
            "Template analytics coletados: %d WABAs, %d templates atualizados, %d erros",
            resultado["total_wabas"],
            resultado["templates_atualizados"],
            resultado["erros"],
        )

        return resultado

    async def _consultar_analytics_api(self, waba_id: str, token: str) -> Optional[list]:
        """
        Consulta analytics via Meta Graph API.

        GET /{waba_id}/message_templates?fields=name,language,quality_score,status
        """
        try:
            client = await get_http_client()
            resp = await client.get(
                f"https://graph.facebook.com/{self.api_version}/{waba_id}/message_templates",
                params={
                    "fields": "name,language,quality_score,status",
                    "limit": 100,
                },
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            )

            if resp.status_code != 200:
                logger.warning(
                    "Template analytics API error WABA %s: %d",
                    waba_id,
                    resp.status_code,
                )
                return None

            data = resp.json()
            return data.get("data", [])

        except Exception as e:
            logger.error("Erro ao consultar template analytics WABA %s: %s", waba_id, e)
            return None

    async def _salvar_analytics(self, waba_id: str, templates: list) -> int:
        """Salva analytics no banco (upsert por WABA/template/language/date)."""
        count = 0
        today = date.today().isoformat()

        for tpl in templates:
            try:
                name = tpl.get("name")
                language = tpl.get("language", "pt_BR")
                if not name:
                    continue

                # Upsert via on_conflict
                supabase.table("meta_template_analytics").upsert(
                    {
                        "waba_id": waba_id,
                        "template_name": name,
                        "language": language,
                        "date": today,
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    on_conflict="waba_id,template_name,language,date",
                ).execute()

                count += 1

            except Exception as e:
                logger.warning("Erro ao salvar analytics template %s: %s", tpl.get("name"), e)

        return count

    async def obter_analytics_template(
        self,
        template_name: str,
        waba_id: Optional[str] = None,
        days: int = 30,
    ) -> list:
        """Obtém analytics de um template específico."""
        try:
            cutoff = (date.today() - timedelta(days=days)).isoformat()
            query = (
                supabase.table("meta_template_analytics")
                .select("*")
                .eq("template_name", template_name)
                .gte("date", cutoff)
            )

            if waba_id:
                query = query.eq("waba_id", waba_id)

            resp = query.order("date", desc=True).execute()
            return resp.data or []

        except Exception as e:
            logger.error("Erro ao obter analytics template %s: %s", template_name, e)
            return []

    async def obter_ranking_templates(
        self,
        waba_id: Optional[str] = None,
        days: int = 7,
        limit: int = 20,
    ) -> list:
        """
        Ranking de templates por delivery rate.

        Returns:
            Lista de dicts com template_name, total_sent, avg_delivery_rate, avg_read_rate.
        """
        try:
            cutoff = (date.today() - timedelta(days=days)).isoformat()

            # Usar SQL para agregação
            waba_filter = f"AND waba_id = '{waba_id}'" if waba_id else ""

            resp = supabase.rpc(
                "execute_sql_query",
                {
                    "query_text": f"""
                        SELECT
                            template_name,
                            SUM(sent_count) as total_sent,
                            AVG(delivery_rate) as avg_delivery_rate,
                            AVG(read_rate) as avg_read_rate,
                            SUM(cost_usd) as total_cost
                        FROM meta_template_analytics
                        WHERE date >= '{cutoff}' {waba_filter}
                        GROUP BY template_name
                        HAVING SUM(sent_count) >= {MIN_SENT_FOR_ANALYSIS}
                        ORDER BY AVG(delivery_rate) DESC
                        LIMIT {limit}
                    """
                },
            ).execute()

            return resp.data or []

        except Exception:
            # Fallback: query simples sem agregação
            try:
                query = (
                    supabase.table("meta_template_analytics")
                    .select("template_name, sent_count, delivery_rate, read_rate, cost_usd")
                    .gte("date", cutoff)
                )
                if waba_id:
                    query = query.eq("waba_id", waba_id)

                resp = query.order("delivery_rate", desc=True).limit(limit).execute()
                return resp.data or []
            except Exception as e:
                logger.error("Erro ao obter ranking templates: %s", e)
                return []

    async def detectar_templates_baixa_performance(
        self,
        waba_id: Optional[str] = None,
        days: int = 7,
    ) -> list:
        """
        Detecta templates com performance abaixo dos thresholds.

        Returns:
            Lista de templates com baixa performance.
        """
        try:
            cutoff = (date.today() - timedelta(days=days)).isoformat()

            query = (
                supabase.table("meta_template_analytics")
                .select("template_name, waba_id, sent_count, delivery_rate, read_rate, date")
                .gte("date", cutoff)
                .gte("sent_count", MIN_SENT_FOR_ANALYSIS)
            )

            if waba_id:
                query = query.eq("waba_id", waba_id)

            resp = query.order("delivery_rate").execute()

            alertas = []
            for row in resp.data or []:
                motivos = []
                dr = row.get("delivery_rate") or 0
                rr = row.get("read_rate") or 0

                if dr < THRESHOLD_DELIVERY_RATE:
                    motivos.append(f"delivery_rate={dr:.1%} (min {THRESHOLD_DELIVERY_RATE:.0%})")
                if rr < THRESHOLD_READ_RATE:
                    motivos.append(f"read_rate={rr:.1%} (min {THRESHOLD_READ_RATE:.0%})")

                if motivos:
                    alertas.append(
                        {
                            "template_name": row["template_name"],
                            "waba_id": row["waba_id"],
                            "sent_count": row["sent_count"],
                            "delivery_rate": dr,
                            "read_rate": rr,
                            "motivos": motivos,
                        }
                    )

            return alertas

        except Exception as e:
            logger.error("Erro ao detectar templates baixa performance: %s", e)
            return []


# Singleton
template_analytics = MetaTemplateAnalytics()
