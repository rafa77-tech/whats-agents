"""
KPIs Operacionais.

Sprint 18 - E12: Data Integrity

3 KPIs que governam a operacao:
- Conversion Rate: offer_made → offer_accepted
- Time-to-Fill: Tempos em cada etapa do funil (desmembrado)
- Health Score: Pressao, friccao, qualidade, spam
"""
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


# =============================================================================
# Conversion Rate
# =============================================================================

@dataclass
class ConversionRate:
    """Taxa de conversao."""
    segment_type: str  # global, hospital, especialidade
    segment_value: str
    offers_made: int
    offers_accepted: int
    conversion_rate: float
    period_hours: int

    @property
    def status(self) -> str:
        """Status baseado na taxa."""
        if self.conversion_rate >= 50:
            return "excellent"
        elif self.conversion_rate >= 30:
            return "good"
        elif self.conversion_rate >= 15:
            return "warning"
        return "critical"


async def get_conversion_rates(
    hours: int = 168,
    hospital_id: Optional[str] = None,
) -> List[ConversionRate]:
    """
    Obtem taxas de conversao.

    Args:
        hours: Janela de tempo
        hospital_id: Filtrar por hospital

    Returns:
        Lista de taxas por segmento
    """
    try:
        response = supabase.rpc(
            "get_conversion_rates",
            {"p_hours": hours, "p_hospital_id": hospital_id}
        ).execute()

        rates = []
        for row in response.data or []:
            made = int(row.get("offers_made") or 0)
            accepted = int(row.get("offers_accepted") or 0)
            rate = (accepted / made * 100) if made > 0 else 0

            rates.append(ConversionRate(
                segment_type=row["segment_type"],
                segment_value=row["segment_value"],
                offers_made=made,
                offers_accepted=accepted,
                conversion_rate=round(rate, 2),
                period_hours=row["period_hours"],
            ))

        # Ordenar por taxa decrescente
        rates.sort(key=lambda x: x.conversion_rate, reverse=True)
        return rates

    except Exception as e:
        logger.error(f"Erro ao obter conversion rates: {e}")
        return []


# =============================================================================
# Time-to-Fill Breakdown
# =============================================================================

@dataclass
class TimeMetric:
    """Metrica de tempo."""
    metric_name: str  # time_to_reserve, time_to_confirm, time_to_fill
    segment_type: str
    segment_value: str
    sample_size: int
    avg_hours: float
    median_hours: float
    p90_hours: float
    p95_hours: float
    min_hours: float
    max_hours: float

    @property
    def avg_days(self) -> float:
        """Media em dias."""
        return round(self.avg_hours / 24, 1)

    @property
    def description(self) -> str:
        """Descricao da metrica."""
        descs = {
            "time_to_reserve": "Anunciada → Reservada (performance Julia)",
            "time_to_confirm": "Pendente → Realizada (performance operacional)",
            "time_to_fill": "Anunciada → Realizada (ROI completo)",
        }
        return descs.get(self.metric_name, self.metric_name)

    @property
    def status(self) -> str:
        """Status baseado no tempo (varia por metrica)."""
        thresholds = {
            "time_to_reserve": {"excellent": 12, "good": 24, "warning": 48},
            "time_to_confirm": {"excellent": 2, "good": 6, "warning": 24},
            "time_to_fill": {"excellent": 24, "good": 48, "warning": 72},
        }
        t = thresholds.get(self.metric_name, {"excellent": 24, "good": 48, "warning": 72})
        if self.avg_hours <= t["excellent"]:
            return "excellent"
        elif self.avg_hours <= t["good"]:
            return "good"
        elif self.avg_hours <= t["warning"]:
            return "warning"
        return "slow"


@dataclass
class TimeToFillBreakdown:
    """Breakdown completo de tempos."""
    time_to_reserve: List[TimeMetric]
    time_to_confirm: List[TimeMetric]
    time_to_fill: List[TimeMetric]

    def get_global_metrics(self) -> Dict[str, Optional[TimeMetric]]:
        """Retorna metricas globais de cada tipo."""
        return {
            "time_to_reserve": next((m for m in self.time_to_reserve if m.segment_type == "global"), None),
            "time_to_confirm": next((m for m in self.time_to_confirm if m.segment_type == "global"), None),
            "time_to_fill": next((m for m in self.time_to_fill if m.segment_type == "global"), None),
        }


async def get_time_to_fill_breakdown(
    days: int = 30,
    hospital_id: Optional[str] = None,
) -> TimeToFillBreakdown:
    """
    Obtem breakdown de tempos.

    Args:
        days: Janela de tempo
        hospital_id: Filtrar por hospital

    Returns:
        TimeToFillBreakdown com as 3 metricas
    """
    try:
        response = supabase.rpc(
            "get_time_to_fill_breakdown",
            {"p_days": days, "p_hospital_id": hospital_id}
        ).execute()

        time_to_reserve: List[TimeMetric] = []
        time_to_confirm: List[TimeMetric] = []
        time_to_fill: List[TimeMetric] = []

        for row in response.data or []:
            metric = TimeMetric(
                metric_name=row["metric_name"],
                segment_type=row["segment_type"],
                segment_value=row["segment_value"],
                sample_size=int(row.get("sample_size") or 0),
                avg_hours=float(row.get("avg_hours") or 0),
                median_hours=float(row.get("median_hours") or 0),
                p90_hours=float(row.get("p90_hours") or 0),
                p95_hours=float(row.get("p95_hours") or 0),
                min_hours=float(row.get("min_hours") or 0),
                max_hours=float(row.get("max_hours") or 0),
            )

            if metric.metric_name == "time_to_reserve":
                time_to_reserve.append(metric)
            elif metric.metric_name == "time_to_confirm":
                time_to_confirm.append(metric)
            elif metric.metric_name == "time_to_fill":
                time_to_fill.append(metric)

        return TimeToFillBreakdown(
            time_to_reserve=time_to_reserve,
            time_to_confirm=time_to_confirm,
            time_to_fill=time_to_fill,
        )

    except Exception as e:
        logger.error(f"Erro ao obter time breakdown: {e}")
        return TimeToFillBreakdown([], [], [])


# =============================================================================
# Health Score
# =============================================================================

@dataclass
class HealthComponent:
    """Componente do Health Score."""
    component: str  # pressao, friccao, qualidade, spam
    metric_name: str
    value: float
    total_count: int
    affected_count: int
    percentage: float
    weight: float


@dataclass
class HealthScore:
    """Score de saude composto."""
    score: float
    status: str
    components: Dict[str, List[HealthComponent]]
    component_scores: Dict[str, float]
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "status": self.status,
            "components": {
                comp: [
                    {
                        "metric": c.metric_name,
                        "value": c.value,
                        "percentage": c.percentage,
                        "total": c.total_count,
                        "affected": c.affected_count,
                    }
                    for c in comps
                ]
                for comp, comps in self.components.items()
            },
            "component_scores": self.component_scores,
            "recommendations": self.recommendations,
        }


async def get_health_score() -> HealthScore:
    """
    Calcula Health Score composto.

    Componentes:
    - Pressao (25%): contact_count_7d acima do limite
    - Friccao (35%): opted_out + cooling_off
    - Qualidade (25%): taxa de handoff
    - Spam (15%): campaign_blocked rate

    Returns:
        HealthScore com breakdown por componente
    """
    try:
        response = supabase.rpc("get_health_score_components").execute()

        # Agrupar por componente
        components: Dict[str, List[HealthComponent]] = {
            "pressao": [],
            "friccao": [],
            "qualidade": [],
            "spam": [],
        }

        for row in response.data or []:
            comp = HealthComponent(
                component=row["component"],
                metric_name=row["metric_name"],
                value=float(row.get("value") or 0),
                total_count=int(row.get("total_count") or 0),
                affected_count=int(row.get("affected_count") or 0),
                percentage=float(row.get("percentage") or 0),
                weight=float(row.get("weight") or 0),
            )
            if comp.component in components:
                components[comp.component].append(comp)

        # Calcular score por componente
        def calc_component_score(comps: List[HealthComponent]) -> float:
            """Quanto maior o %, pior o score."""
            if not comps:
                return 0
            # Usar a maior porcentagem do componente
            max_pct = max(c.percentage for c in comps) if comps else 0
            # Normalizar: 0% = 0 pontos negativos, 50%+ = 50 pontos negativos
            return min(50, max_pct)

        component_scores = {
            "pressao": calc_component_score(components["pressao"]),
            "friccao": calc_component_score(components["friccao"]),
            "qualidade": calc_component_score(components["qualidade"]),
            "spam": calc_component_score(components["spam"]),
        }

        # Score final = 100 - impactos ponderados
        score = 100 - (
            component_scores["pressao"] * 0.25 +
            component_scores["friccao"] * 0.35 +
            component_scores["qualidade"] * 0.25 +
            component_scores["spam"] * 0.15
        )
        score = max(0, min(100, score))

        # Status
        if score >= 80:
            status = "healthy"
        elif score >= 60:
            status = "attention"
        elif score >= 40:
            status = "risk"
        else:
            status = "critical"

        # Recomendacoes baseadas em componentes
        recommendations: List[str] = []

        # Pressao
        pressao_metrics = components.get("pressao", [])
        if any(c.percentage > 20 for c in pressao_metrics):
            recommendations.append("Reduzir frequencia de contatos (pressao alta)")

        # Friccao
        friccao_metrics = components.get("friccao", [])
        opted_out = next((c for c in friccao_metrics if c.metric_name == "opted_out_rate"), None)
        cooling = next((c for c in friccao_metrics if c.metric_name == "cooling_off_rate"), None)
        if opted_out and opted_out.percentage > 5:
            recommendations.append("Revisar qualidade das abordagens (opt-out alto)")
        if cooling and cooling.percentage > 10:
            recommendations.append("Resolver objecoes antes de novos contatos")

        # Qualidade
        qualidade_metrics = components.get("qualidade", [])
        if any(c.percentage > 15 for c in qualidade_metrics):
            recommendations.append("Investigar causas de handoff (crise frequente)")

        # Spam
        spam_metrics = components.get("spam", [])
        if any(c.percentage > 10 for c in spam_metrics):
            recommendations.append("Revisar filtros de campanha (muitos bloqueios)")

        # Critical action
        if status == "critical":
            recommendations.insert(0, "PAUSAR campanhas imediatamente")

        return HealthScore(
            score=round(score, 1),
            status=status,
            components=components,
            component_scores=component_scores,
            recommendations=recommendations,
        )

    except Exception as e:
        logger.error(f"Erro ao calcular health score: {e}")
        return HealthScore(
            score=0,
            status="unknown",
            components={},
            component_scores={},
            recommendations=["Erro ao calcular - verificar logs"],
        )


# =============================================================================
# Resumo Executivo
# =============================================================================

async def get_kpis_summary() -> dict:
    """
    Retorna resumo dos 3 KPIs principais.

    Usado como dashboard executivo.
    """
    conversion = await get_conversion_rates(hours=168)
    time_breakdown = await get_time_to_fill_breakdown(days=30)
    health = await get_health_score()

    # Globais
    conv_global = next((c for c in conversion if c.segment_type == "global"), None)
    time_globals = time_breakdown.get_global_metrics()

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "kpis": {
            "conversion_rate": {
                "value": conv_global.conversion_rate if conv_global else 0,
                "status": conv_global.status if conv_global else "unknown",
                "offers_made": conv_global.offers_made if conv_global else 0,
                "offers_accepted": conv_global.offers_accepted if conv_global else 0,
            },
            "time_to_fill": {
                "time_to_reserve": {
                    "avg_hours": time_globals["time_to_reserve"].avg_hours if time_globals["time_to_reserve"] else 0,
                    "status": time_globals["time_to_reserve"].status if time_globals["time_to_reserve"] else "unknown",
                },
                "time_to_confirm": {
                    "avg_hours": time_globals["time_to_confirm"].avg_hours if time_globals["time_to_confirm"] else 0,
                    "status": time_globals["time_to_confirm"].status if time_globals["time_to_confirm"] else "unknown",
                },
                "time_to_fill_full": {
                    "avg_hours": time_globals["time_to_fill"].avg_hours if time_globals["time_to_fill"] else 0,
                    "status": time_globals["time_to_fill"].status if time_globals["time_to_fill"] else "unknown",
                },
            },
            "health_score": {
                "score": health.score,
                "status": health.status,
                "component_scores": health.component_scores,
                "recommendations": health.recommendations[:3],  # Top 3
            },
        },
    }
