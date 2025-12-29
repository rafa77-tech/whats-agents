# Epic 12: Metricas que Importam (3 KPIs Operacionais)

## Objetivo

Criar 3 KPIs que governam a operacao, saindo de metricas cruas (contagens) para indicadores acionaveis.

## Contexto

### O Problema

Temos metricas brutas (contagens de eventos), mas faltam indicadores que:
- Governam decisoes de negocio
- Mostram saude da operacao
- Previnem crescimento que queima a base

### A Solucao

Tres KPIs consolidados:

| KPI | O que mede | Por que importa |
|-----|------------|-----------------|
| **Conversion Rate** | offer_made → offer_accepted | Eficacia das ofertas |
| **Time-to-Fill** | Tempos em cada etapa do funil | Velocidade operacional |
| **Health Score** | Pressao, friccao, qualidade | Sustentabilidade do crescimento |

---

## Story 12.1: Conversion Rate por Etapa

### Objetivo
Medir taxa de conversao em cada etapa do funil, segmentada.

### Formula

```
Conversion Rate = (offer_accepted / offer_made) * 100
```

### Segmentacoes

- Por hospital
- Por origem do medico (campanha, inbound, referral)
- Por faixa de risco da vaga
- Por especialidade
- Por periodo (dia/semana/mes)

### Tarefas

1. **Funcao SQL**

```sql
CREATE OR REPLACE FUNCTION get_conversion_rates(
    p_hours INT DEFAULT 168,  -- 7 dias default
    p_hospital_id UUID DEFAULT NULL
)
RETURNS TABLE (
    segment_type TEXT,
    segment_value TEXT,
    offers_made BIGINT,
    offers_accepted BIGINT,
    conversion_rate NUMERIC(5,2),
    period_hours INT
) AS $$
BEGIN
    RETURN QUERY

    -- Taxa geral
    SELECT
        'global'::TEXT,
        'all'::TEXT,
        (SELECT COUNT(*) FROM business_events WHERE event_type = 'offer_made' AND ts >= now() - (p_hours || ' hours')::interval),
        (SELECT COUNT(*) FROM business_events WHERE event_type = 'offer_accepted' AND ts >= now() - (p_hours || ' hours')::interval),
        0::NUMERIC(5,2),
        p_hours

    UNION ALL

    -- Por hospital
    SELECT
        'hospital'::TEXT,
        COALESCE(h.nome, be.hospital_id::TEXT),
        COUNT(*) FILTER (WHERE be.event_type = 'offer_made'),
        COUNT(*) FILTER (WHERE be.event_type = 'offer_accepted'),
        0::NUMERIC(5,2),
        p_hours
    FROM business_events be
    LEFT JOIN hospitais h ON be.hospital_id = h.id
    WHERE be.event_type IN ('offer_made', 'offer_accepted')
      AND be.ts >= now() - (p_hours || ' hours')::interval
      AND be.hospital_id IS NOT NULL
      AND (p_hospital_id IS NULL OR be.hospital_id = p_hospital_id)
    GROUP BY be.hospital_id, h.nome
    HAVING COUNT(*) FILTER (WHERE be.event_type = 'offer_made') >= 5;  -- Minimo de ofertas

END;
$$ LANGUAGE plpgsql;
```

2. **Servico Python**

```python
# app/services/business_events/kpis.py

import logging
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from typing import List, Optional, Dict

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


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
            made = row["offers_made"] or 0
            accepted = row["offers_accepted"] or 0
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
```

### DoD

- [ ] Funcao SQL `get_conversion_rates` criada
- [ ] Segmentacao por hospital funcionando
- [ ] Servico Python implementado
- [ ] Status calculado (excellent/good/warning/critical)

---

## Story 12.2: Time-to-Fill (Desmembrado)

### Objetivo
Medir tempo em cada etapa do funil, separando responsabilidades.

### Tres Metricas de Tempo

| Metrica | De → Para | O que mede |
|---------|-----------|------------|
| **Time-to-Reserve** | anunciada → reservada | Performance de "vender" o plantao (Julia) |
| **Time-to-Confirm** | pendente_confirmacao → realizada/cancelada | Performance operacional (Slack/humano) |
| **Time-to-Fill (full)** | anunciada → realizada | Metrica de ROI completa |

### Por que desmembrar?

- **Time-to-Reserve** isola a performance da Julia em fechar vagas
- **Time-to-Confirm** isola atraso humano no Slack (gestor confirma)
- **Time-to-Fill** e a metrica de ROI mas mistura responsabilidades

### Funcao SQL

```sql
CREATE OR REPLACE FUNCTION get_time_to_fill_breakdown(
    p_days INT DEFAULT 30,
    p_hospital_id UUID DEFAULT NULL
)
RETURNS TABLE (
    metric_name TEXT,
    segment_type TEXT,
    segment_value TEXT,
    sample_size BIGINT,
    avg_hours NUMERIC(10,2),
    median_hours NUMERIC(10,2),
    p90_hours NUMERIC(10,2),
    p95_hours NUMERIC(10,2),
    min_hours NUMERIC(10,2),
    max_hours NUMERIC(10,2)
) AS $$
BEGIN
    -- Time-to-Reserve: anunciada → reservada
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
                - v.created_at
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status IN ('reservada', 'pendente_confirmacao', 'realizada')
          AND v.created_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
    )
    SELECT
        'time_to_reserve'::TEXT,
        'global'::TEXT,
        'all'::TEXT,
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0;

    -- Time-to-Reserve por hospital
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
                - v.created_at
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status IN ('reservada', 'pendente_confirmacao', 'realizada')
          AND v.created_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'offer_accepted')
    )
    SELECT
        'time_to_reserve'::TEXT,
        'hospital'::TEXT,
        COALESCE(hospital_nome, hospital_id::TEXT),
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0
    GROUP BY hospital_id, hospital_nome
    HAVING COUNT(*) >= 3;

    -- Time-to-Confirm: pendente_confirmacao → realizada/cancelada
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                COALESCE(
                    (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_completed'),
                    (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_cancelled')
                )
                - (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_pending_confirmation')
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status IN ('realizada', 'cancelada')
          AND v.updated_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_pending_confirmation')
    )
    SELECT
        'time_to_confirm'::TEXT,
        'global'::TEXT,
        'all'::TEXT,
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0 AND horas IS NOT NULL;

    -- Time-to-Fill (full): anunciada → realizada
    RETURN QUERY
    WITH tempos AS (
        SELECT
            v.id,
            v.hospital_id,
            h.nome as hospital_nome,
            EXTRACT(EPOCH FROM (
                (SELECT MIN(ts) FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_completed')
                - v.created_at
            )) / 3600 as horas
        FROM vagas v
        LEFT JOIN hospitais h ON v.hospital_id = h.id
        WHERE v.status = 'realizada'
          AND v.updated_at >= now() - (p_days || ' days')::interval
          AND (p_hospital_id IS NULL OR v.hospital_id = p_hospital_id)
          AND EXISTS (SELECT 1 FROM business_events be WHERE be.vaga_id = v.id AND be.event_type = 'shift_completed')
    )
    SELECT
        'time_to_fill'::TEXT,
        'global'::TEXT,
        'all'::TEXT,
        COUNT(*),
        ROUND(AVG(horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY horas)::NUMERIC, 2),
        ROUND(MIN(horas)::NUMERIC, 2),
        ROUND(MAX(horas)::NUMERIC, 2)
    FROM tempos
    WHERE horas > 0;

END;
$$ LANGUAGE plpgsql;
```

### Servico Python

```python
# app/services/business_events/kpis.py (adicao)

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

        time_to_reserve = []
        time_to_confirm = []
        time_to_fill = []

        for row in response.data or []:
            metric = TimeMetric(
                metric_name=row["metric_name"],
                segment_type=row["segment_type"],
                segment_value=row["segment_value"],
                sample_size=row["sample_size"] or 0,
                avg_hours=row["avg_hours"] or 0,
                median_hours=row["median_hours"] or 0,
                p90_hours=row["p90_hours"] or 0,
                p95_hours=row["p95_hours"] or 0,
                min_hours=row["min_hours"] or 0,
                max_hours=row["max_hours"] or 0,
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
```

### DoD

- [ ] Funcao SQL `get_time_to_fill_breakdown` criada
- [ ] 3 metricas separadas: reserve, confirm, fill
- [ ] Percentis (P50, P90, P95) calculados
- [ ] Status com thresholds diferentes por metrica

---

## Story 12.3: Health Score (Composto)

### Objetivo
Medir saude da base com 4 componentes distintos.

### Componentes do Health Score

| Componente | O que mede | Peso | Fonte |
|------------|------------|------|-------|
| **Pressao** | contact_count_7d (media e P95) | 25% | doctor_state |
| **Friccao** | Taxa cooling_off + opted_out | 35% | doctor_state |
| **Qualidade** | Taxa de handoff (crise/objecao grave) | 25% | business_events |
| **Spam** | campaign_blocked / outbound_attempts | 15% | business_events |

### Formula

```
Health Score = 100 - (
    pressao_score * 0.25 +
    friccao_score * 0.35 +
    qualidade_score * 0.25 +
    spam_score * 0.15
)
```

### Funcao SQL

```sql
CREATE OR REPLACE FUNCTION get_health_score_components()
RETURNS TABLE (
    component TEXT,
    metric_name TEXT,
    value NUMERIC(10,2),
    total_count BIGINT,
    affected_count BIGINT,
    percentage NUMERIC(5,2),
    weight NUMERIC(3,2)
) AS $$
DECLARE
    v_total_doctors BIGINT;
    v_contact_avg NUMERIC(10,2);
    v_contact_p95 NUMERIC(10,2);
    v_opted_out BIGINT;
    v_cooling_off BIGINT;
    v_handoffs_7d BIGINT;
    v_conversations_7d BIGINT;
    v_blocked_7d BIGINT;
    v_outbound_7d BIGINT;
BEGIN
    -- Total de medicos com state
    SELECT COUNT(*) INTO v_total_doctors FROM doctor_state;

    -- COMPONENTE 1: Pressao (contact_count_7d)
    SELECT
        ROUND(AVG(contact_count_7d)::NUMERIC, 2),
        ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY contact_count_7d)::NUMERIC, 2)
    INTO v_contact_avg, v_contact_p95
    FROM doctor_state;

    RETURN QUERY SELECT
        'pressao'::TEXT,
        'contact_count_7d_avg'::TEXT,
        COALESCE(v_contact_avg, 0),
        v_total_doctors,
        (SELECT COUNT(*) FROM doctor_state WHERE contact_count_7d > 5),
        CASE WHEN v_total_doctors > 0 THEN
            ROUND(((SELECT COUNT(*) FROM doctor_state WHERE contact_count_7d > 5)::NUMERIC / v_total_doctors) * 100, 2)
        ELSE 0 END,
        0.25::NUMERIC;

    RETURN QUERY SELECT
        'pressao'::TEXT,
        'contact_count_7d_p95'::TEXT,
        COALESCE(v_contact_p95, 0),
        v_total_doctors,
        0::BIGINT,
        0::NUMERIC,
        0::NUMERIC;

    -- COMPONENTE 2: Friccao (opted_out + cooling_off)
    SELECT COUNT(*) INTO v_opted_out FROM doctor_state WHERE permission_state = 'opted_out';
    SELECT COUNT(*) INTO v_cooling_off FROM doctor_state WHERE permission_state = 'cooling_off';

    RETURN QUERY SELECT
        'friccao'::TEXT,
        'opted_out_rate'::TEXT,
        0::NUMERIC,
        v_total_doctors,
        v_opted_out,
        CASE WHEN v_total_doctors > 0 THEN ROUND((v_opted_out::NUMERIC / v_total_doctors) * 100, 2) ELSE 0 END,
        0.175::NUMERIC;

    RETURN QUERY SELECT
        'friccao'::TEXT,
        'cooling_off_rate'::TEXT,
        0::NUMERIC,
        v_total_doctors,
        v_cooling_off,
        CASE WHEN v_total_doctors > 0 THEN ROUND((v_cooling_off::NUMERIC / v_total_doctors) * 100, 2) ELSE 0 END,
        0.175::NUMERIC;

    -- COMPONENTE 3: Qualidade (handoff rate)
    SELECT COUNT(*) INTO v_handoffs_7d
    FROM business_events
    WHERE event_type = 'handoff_started'
      AND ts >= now() - interval '7 days';

    SELECT COUNT(DISTINCT cliente_id) INTO v_conversations_7d
    FROM business_events
    WHERE event_type IN ('doctor_inbound', 'doctor_outbound')
      AND ts >= now() - interval '7 days';

    RETURN QUERY SELECT
        'qualidade'::TEXT,
        'handoff_rate'::TEXT,
        0::NUMERIC,
        COALESCE(v_conversations_7d, 0),
        v_handoffs_7d,
        CASE WHEN v_conversations_7d > 0 THEN ROUND((v_handoffs_7d::NUMERIC / v_conversations_7d) * 100, 2) ELSE 0 END,
        0.25::NUMERIC;

    -- COMPONENTE 4: Spam (campaign_blocked rate)
    SELECT COUNT(*) INTO v_blocked_7d
    FROM business_events
    WHERE event_type = 'campaign_blocked'
      AND ts >= now() - interval '7 days';

    SELECT COUNT(*) INTO v_outbound_7d
    FROM business_events
    WHERE event_type = 'doctor_outbound'
      AND ts >= now() - interval '7 days';

    RETURN QUERY SELECT
        'spam'::TEXT,
        'blocked_rate'::TEXT,
        0::NUMERIC,
        COALESCE(v_outbound_7d, 0),
        v_blocked_7d,
        CASE WHEN v_outbound_7d > 0 THEN ROUND((v_blocked_7d::NUMERIC / v_outbound_7d) * 100, 2) ELSE 0 END,
        0.15::NUMERIC;

END;
$$ LANGUAGE plpgsql;
```

### Servico Python

```python
# app/services/business_events/kpis.py (adicao)

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
                value=row["value"] or 0,
                total_count=row["total_count"] or 0,
                affected_count=row["affected_count"] or 0,
                percentage=row["percentage"] or 0,
                weight=row["weight"] or 0,
            )
            if comp.component in components:
                components[comp.component].append(comp)

        # Calcular score por componente
        def calc_component_score(comps: List[HealthComponent]) -> float:
            """Quanto maior o %, pior o score."""
            if not comps:
                return 0
            # Usar a maior porcentagem do componente
            max_pct = max(c.percentage for c in comps)
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
        recommendations = []

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
```

### DoD

- [ ] Funcao SQL `get_health_score_components` criada
- [ ] 4 componentes implementados (pressao, friccao, qualidade, spam)
- [ ] Pesos aplicados corretamente
- [ ] Recomendacoes por componente

---

## Story 12.4: Endpoints de KPIs

### Objetivo
Expor KPIs via API para dashboard.

### Tarefas

```python
# app/api/routes/metricas.py (adicao)

@router.get("/kpis")
async def kpis_resumo():
    """
    Retorna resumo dos 3 KPIs principais.

    Usado como dashboard executivo.
    """
    from app.services.business_events.kpis import (
        get_conversion_rates,
        get_time_to_fill_breakdown,
        get_health_score,
    )

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


@router.get("/kpis/conversion")
async def kpis_conversion(
    hours: int = Query(168, ge=24, le=720),
    hospital_id: Optional[str] = None,
):
    """Detalhes de Conversion Rate."""
    from app.services.business_events.kpis import get_conversion_rates
    rates = await get_conversion_rates(hours, hospital_id)
    return {
        "period_hours": hours,
        "segments": [
            {
                "type": r.segment_type,
                "value": r.segment_value,
                "offers_made": r.offers_made,
                "offers_accepted": r.offers_accepted,
                "conversion_rate": r.conversion_rate,
                "status": r.status,
            }
            for r in rates
        ],
    }


@router.get("/kpis/time-to-fill")
async def kpis_time_to_fill(
    days: int = Query(30, ge=7, le=90),
    hospital_id: Optional[str] = None,
):
    """Detalhes de Time-to-Fill (breakdown)."""
    from app.services.business_events.kpis import get_time_to_fill_breakdown
    breakdown = await get_time_to_fill_breakdown(days, hospital_id)

    def serialize_metrics(metrics: List) -> List[dict]:
        return [
            {
                "segment_type": m.segment_type,
                "segment_value": m.segment_value,
                "description": m.description,
                "sample_size": m.sample_size,
                "avg_hours": m.avg_hours,
                "avg_days": m.avg_days,
                "median_hours": m.median_hours,
                "p90_hours": m.p90_hours,
                "p95_hours": m.p95_hours,
                "status": m.status,
            }
            for m in metrics
        ]

    return {
        "period_days": days,
        "time_to_reserve": serialize_metrics(breakdown.time_to_reserve),
        "time_to_confirm": serialize_metrics(breakdown.time_to_confirm),
        "time_to_fill": serialize_metrics(breakdown.time_to_fill),
    }


@router.get("/kpis/health")
async def kpis_health():
    """Detalhes de Health Score (componentes)."""
    from app.services.business_events.kpis import get_health_score
    health = await get_health_score()
    return health.to_dict()
```

### DoD

- [ ] Endpoint `/metricas/kpis` com resumo executivo
- [ ] Endpoint `/metricas/kpis/conversion` funcionando
- [ ] Endpoint `/metricas/kpis/time-to-fill` com breakdown
- [ ] Endpoint `/metricas/kpis/health` com componentes

---

## Checklist do Epico

- [ ] **S18.E12.1** - Conversion Rate implementado
- [ ] **S18.E12.2** - Time-to-Fill desmembrado (reserve, confirm, fill)
- [ ] **S18.E12.3** - Health Score composto (4 componentes)
- [ ] **S18.E12.4** - Endpoints de KPIs funcionando
- [ ] Thresholds diferentes por metrica de tempo
- [ ] Recomendacoes por componente do Health Score
- [ ] Breakdown evita contaminacao por atraso humano
