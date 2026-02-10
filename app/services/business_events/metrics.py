"""
Métricas de funil de negócio.

Sprint 17 - E06

Queries e agregações para métricas de conversão.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class FunnelMetrics:
    """Métricas de funil."""

    period_hours: int
    hospital_id: Optional[str] = None

    # Contagens
    doctor_outbound: int = 0
    doctor_inbound: int = 0
    offer_teaser_sent: int = 0
    offer_made: int = 0
    offer_declined: int = 0
    offer_accepted: int = 0
    handoff_created: int = 0
    shift_completed: int = 0

    # Taxas (%)
    response_rate: float = 0.0
    conversion_rate: float = 0.0
    completion_rate: float = 0.0
    overall_success: float = 0.0

    def to_dict(self) -> dict:
        """Serializa para resposta de API."""
        return {
            "period_hours": self.period_hours,
            "hospital_id": self.hospital_id,
            "counts": {
                "doctor_outbound": self.doctor_outbound,
                "doctor_inbound": self.doctor_inbound,
                "offer_teaser_sent": self.offer_teaser_sent,
                "offer_made": self.offer_made,
                "offer_declined": self.offer_declined,
                "offer_accepted": self.offer_accepted,
                "handoff_created": self.handoff_created,
                "shift_completed": self.shift_completed,
            },
            "rates": {
                "response_rate": self.response_rate,
                "conversion_rate": self.conversion_rate,
                "completion_rate": self.completion_rate,
                "overall_success": self.overall_success,
            },
        }


async def get_funnel_metrics(
    hours: int = 24,
    hospital_id: Optional[str] = None,
) -> FunnelMetrics:
    """
    Obtém métricas de funil.

    Args:
        hours: Janela de tempo em horas
        hospital_id: Filtrar por hospital (opcional)

    Returns:
        FunnelMetrics com contagens e taxas
    """
    metrics = FunnelMetrics(period_hours=hours, hospital_id=hospital_id)

    try:
        # Chamar função SQL de contagem
        response = supabase.rpc(
            "count_business_events", {"p_hours": hours, "p_hospital_id": hospital_id}
        ).execute()

        # Preencher contagens
        for row in response.data or []:
            event_type = row.get("event_type")
            count = row.get("count", 0)

            if event_type == "doctor_outbound":
                metrics.doctor_outbound = count
            elif event_type == "doctor_inbound":
                metrics.doctor_inbound = count
            elif event_type == "offer_teaser_sent":
                metrics.offer_teaser_sent = count
            elif event_type == "offer_made":
                metrics.offer_made = count
            elif event_type == "offer_declined":
                metrics.offer_declined = count
            elif event_type == "offer_accepted":
                metrics.offer_accepted = count
            elif event_type == "handoff_created":
                metrics.handoff_created = count
            elif event_type == "shift_completed":
                metrics.shift_completed = count

        # Calcular taxas
        if metrics.doctor_outbound > 0:
            metrics.response_rate = round(
                (metrics.doctor_inbound / metrics.doctor_outbound) * 100, 2
            )
            metrics.overall_success = round(
                (metrics.shift_completed / metrics.doctor_outbound) * 100, 2
            )

        if metrics.offer_made > 0:
            metrics.conversion_rate = round((metrics.offer_accepted / metrics.offer_made) * 100, 2)

        if metrics.offer_accepted > 0:
            metrics.completion_rate = round(
                (metrics.shift_completed / metrics.offer_accepted) * 100, 2
            )

        return metrics

    except Exception as e:
        logger.error(f"Erro ao obter métricas de funil: {e}")
        return metrics


async def get_funnel_by_hospital(hours: int = 24) -> List[dict]:
    """
    Obtém funil segmentado por hospital.

    Args:
        hours: Janela de tempo

    Returns:
        Lista de métricas por hospital
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # Buscar hospitais únicos com eventos
        response = (
            supabase.table("business_events")
            .select("hospital_id")
            .gte("ts", since)
            .not_.is_("hospital_id", "null")
            .execute()
        )

        # Dedupe hospitais
        hospital_ids = list(set(row["hospital_id"] for row in response.data or []))

        # Obter métricas de cada hospital
        results = []
        for hospital_id in hospital_ids:
            metrics = await get_funnel_metrics(hours=hours, hospital_id=hospital_id)
            results.append(metrics.to_dict())

        # Ordenar por sucesso geral
        results.sort(key=lambda x: x["rates"]["overall_success"], reverse=True)

        return results

    except Exception as e:
        logger.error(f"Erro ao obter funil por hospital: {e}")
        return []


async def get_funnel_trend(
    days: int = 7,
    hospital_id: Optional[str] = None,
) -> List[dict]:
    """
    Obtém tendência do funil nos últimos N dias.

    Args:
        days: Número de dias
        hospital_id: Filtrar por hospital

    Returns:
        Lista de métricas diárias
    """
    results = []

    for i in range(days):
        # Calcular janela do dia
        end = datetime.now(timezone.utc) - timedelta(days=i)
        start = end - timedelta(days=1)

        try:
            since = start.isoformat()
            until = end.isoformat()

            # Query manual para período específico
            query = (
                supabase.table("business_events")
                .select("event_type")
                .gte("ts", since)
                .lt("ts", until)
            )

            if hospital_id:
                query = query.eq("hospital_id", hospital_id)

            data = query.execute().data or []

            # Contar por tipo
            counts = {}
            for row in data:
                event_type = row["event_type"]
                counts[event_type] = counts.get(event_type, 0) + 1

            results.append(
                {
                    "date": end.strftime("%Y-%m-%d"),
                    "counts": counts,
                }
            )

        except Exception as e:
            logger.error(f"Erro ao obter tendência dia {i}: {e}")
            continue

    return list(reversed(results))  # Ordem cronológica


async def get_top_doctors(
    hours: int = 168,  # 7 dias default
    limit: int = 50,
) -> List[dict]:
    """
    Obtém médicos mais ativos (temperatura operacional).

    Args:
        hours: Janela de tempo
        limit: Número máximo de resultados

    Returns:
        Lista de médicos ordenados por atividade
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        response = (
            supabase.table("business_events")
            .select("cliente_id")
            .gte("ts", since)
            .not_.is_("cliente_id", "null")
            .execute()
        )

        # Contar eventos por cliente
        cliente_counts = {}
        for row in response.data or []:
            cliente_id = row["cliente_id"]
            cliente_counts[cliente_id] = cliente_counts.get(cliente_id, 0) + 1

        # Ordenar e limitar
        sorted_clientes = sorted(cliente_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            {"cliente_id": cliente_id, "events": count} for cliente_id, count in sorted_clientes
        ]

    except Exception as e:
        logger.error(f"Erro ao obter top doctors: {e}")
        return []


async def get_conversion_time(
    hours: int = 720,  # 30 dias default
    hospital_id: Optional[str] = None,
) -> dict:
    """
    Obtém tempo médio de conversão.

    Args:
        hours: Janela de tempo
        hospital_id: Filtrar por hospital

    Returns:
        Dict com tempos médios em horas
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        # Buscar eventos por vaga
        query = (
            supabase.table("business_events")
            .select("vaga_id, event_type, ts")
            .gte("ts", since)
            .not_.is_("vaga_id", "null")
            .in_("event_type", ["offer_made", "offer_accepted", "shift_completed"])
        )

        if hospital_id:
            query = query.eq("hospital_id", hospital_id)

        data = query.execute().data or []

        # Agrupar por vaga
        vagas = {}
        for row in data:
            vaga_id = row["vaga_id"]
            if vaga_id not in vagas:
                vagas[vaga_id] = {}
            vagas[vaga_id][row["event_type"]] = row["ts"]

        # Calcular tempos
        made_to_accepted = []
        accepted_to_completed = []

        for vaga_data in vagas.values():
            if "offer_made" in vaga_data and "offer_accepted" in vaga_data:
                made = datetime.fromisoformat(vaga_data["offer_made"].replace("Z", "+00:00"))
                accepted = datetime.fromisoformat(
                    vaga_data["offer_accepted"].replace("Z", "+00:00")
                )
                delta_hours = (accepted - made).total_seconds() / 3600
                if delta_hours >= 0:
                    made_to_accepted.append(delta_hours)

            if "offer_accepted" in vaga_data and "shift_completed" in vaga_data:
                accepted = datetime.fromisoformat(
                    vaga_data["offer_accepted"].replace("Z", "+00:00")
                )
                completed = datetime.fromisoformat(
                    vaga_data["shift_completed"].replace("Z", "+00:00")
                )
                delta_hours = (completed - accepted).total_seconds() / 3600
                if delta_hours >= 0:
                    accepted_to_completed.append(delta_hours)

        return {
            "period_hours": hours,
            "hospital_id": hospital_id,
            "avg_hours_made_to_accepted": round(sum(made_to_accepted) / len(made_to_accepted), 2)
            if made_to_accepted
            else None,
            "avg_hours_accepted_to_completed": round(
                sum(accepted_to_completed) / len(accepted_to_completed), 2
            )
            if accepted_to_completed
            else None,
            "sample_size_made_to_accepted": len(made_to_accepted),
            "sample_size_accepted_to_completed": len(accepted_to_completed),
        }

    except Exception as e:
        logger.error(f"Erro ao calcular tempo de conversão: {e}")
        return {
            "period_hours": hours,
            "hospital_id": hospital_id,
            "avg_hours_made_to_accepted": None,
            "avg_hours_accepted_to_completed": None,
            "sample_size_made_to_accepted": 0,
            "sample_size_accepted_to_completed": 0,
        }
