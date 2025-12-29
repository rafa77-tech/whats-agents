# Epic 06: Queries de Funil

## Objetivo

Implementar queries para calcular métricas de funil e taxas de conversão.

## Contexto

### Funil de Negócio

```
doctor_outbound (mensagens enviadas)
        ↓
doctor_inbound (médicos responderam)
        ↓
offer_teaser_sent (mencionou oportunidades)
        ↓
offer_made (ofereceu vaga específica)
        ↓
offer_accepted (médico aceitou)
        ↓
shift_completed (plantão realizado)
```

### Métricas Principais

| Métrica | Fórmula | Significado |
|---------|---------|-------------|
| Taxa de Resposta | inbound / outbound | % médicos que respondem |
| Taxa de Oferta | offer_made / outbound | % conversas com oferta |
| Taxa de Conversão | accepted / offer_made | % ofertas aceitas |
| Taxa de Conclusão | completed / accepted | % aceites que realizam |
| Funil Completo | completed / outbound | % geral de sucesso |

---

## Story 6.1: As 5 Queries do Funil (Recomendação do Professor)

### Objetivo
Implementar as 5 queries principais para métricas de funil.

### Q1 — Volume por Etapa (últimos 7 dias)

Conta quantos eventos entraram em cada etapa do funil.

```sql
WITH base AS (
  SELECT *
  FROM public.business_events
  WHERE ts >= now() - interval '7 days'
)
SELECT event_type, COUNT(*) AS n
FROM base
WHERE event_type IN (
  'doctor_inbound','doctor_outbound',
  'offer_teaser_sent','offer_made','offer_accepted',
  'offer_declined','handoff_created','shift_completed'
)
GROUP BY event_type
ORDER BY n DESC;
```

### Q2 — Conversão offer_made → offer_accepted (geral e por hospital)

```sql
WITH ev AS (
  SELECT vaga_id, hospital_id,
         MIN(ts) FILTER (WHERE event_type='offer_made') AS offer_made_at,
         MIN(ts) FILTER (WHERE event_type='offer_accepted') AS offer_accepted_at
  FROM public.business_events
  WHERE ts >= now() - interval '7 days'
    AND vaga_id IS NOT NULL
  GROUP BY vaga_id, hospital_id
)
SELECT
  hospital_id,
  COUNT(*) FILTER (WHERE offer_made_at IS NOT NULL) AS offers,
  COUNT(*) FILTER (WHERE offer_accepted_at IS NOT NULL) AS accepts,
  ROUND(
    COUNT(*) FILTER (WHERE offer_accepted_at IS NOT NULL)::numeric
    / NULLIF(COUNT(*) FILTER (WHERE offer_made_at IS NOT NULL),0) * 100, 2
  ) AS accept_rate_pct
FROM ev
GROUP BY hospital_id
ORDER BY accept_rate_pct DESC NULLS LAST;
```

### Q3 — Tempo Médio de Conversão (offer_made → accepted → completed)

```sql
WITH ev AS (
  SELECT vaga_id,
    MIN(ts) FILTER (WHERE event_type='offer_made') AS made_at,
    MIN(ts) FILTER (WHERE event_type='offer_accepted') AS accepted_at,
    MIN(ts) FILTER (WHERE event_type='shift_completed') AS completed_at
  FROM public.business_events
  WHERE ts >= now() - interval '30 days'
    AND vaga_id IS NOT NULL
  GROUP BY vaga_id
)
SELECT
  ROUND(AVG(EXTRACT(EPOCH FROM (accepted_at - made_at))/3600)::numeric, 2) AS hrs_made_to_accepted,
  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - accepted_at))/3600)::numeric, 2) AS hrs_accepted_to_completed
FROM ev
WHERE made_at IS NOT NULL AND accepted_at IS NOT NULL;
```

### Q4 — Atividade por Médico (temperatura operacional)

Top médicos com mais eventos (proxy de "base quente").

```sql
SELECT cliente_id, COUNT(*) AS events_7d
FROM public.business_events
WHERE ts >= now() - interval '7 days'
  AND cliente_id IS NOT NULL
GROUP BY cliente_id
ORDER BY events_7d DESC
LIMIT 50;
```

### Q5 — Qualidade Operacional: Taxa de Handoff por Hospital

```sql
SELECT hospital_id,
       COUNT(*) FILTER (WHERE event_type='handoff_created') AS handoffs,
       COUNT(*) FILTER (WHERE event_type='offer_made') AS offers,
       ROUND(
         COUNT(*) FILTER (WHERE event_type='handoff_created')::numeric
         / NULLIF(COUNT(*) FILTER (WHERE event_type='offer_made'),0) * 100, 2
       ) AS handoff_per_offer_pct
FROM public.business_events
WHERE ts >= now() - interval '7 days'
GROUP BY hospital_id
ORDER BY handoff_per_offer_pct DESC NULLS LAST;
```

### DoD

- [ ] Q1 funcionando (volume por etapa)
- [ ] Q2 funcionando (conversão por hospital)
- [ ] Q3 funcionando (tempo médio)
- [ ] Q4 funcionando (atividade por médico)
- [ ] Q5 funcionando (taxa de handoff)
- [ ] Queries parametrizáveis por período

---

## Story 6.2: Funções SQL de Agregação

### Objetivo
Criar funções SQL reutilizáveis para queries de funil performáticas.

### Tarefas

1. **Criar função de contagem por período**:

```sql
-- Migration: create_funnel_functions
-- Sprint 17 - E06

-- Função para contar eventos por tipo em período
CREATE OR REPLACE FUNCTION count_business_events(
    p_hours INT DEFAULT 24,
    p_hospital_id UUID DEFAULT NULL
)
RETURNS TABLE (
    event_type TEXT,
    count BIGINT
)
LANGUAGE plpgsql AS $$
BEGIN
    RETURN QUERY
    SELECT
        be.event_type,
        COUNT(*)::BIGINT
    FROM business_events be
    WHERE be.ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR be.hospital_id = p_hospital_id)
    GROUP BY be.event_type
    ORDER BY
        CASE be.event_type
            WHEN 'doctor_outbound' THEN 1
            WHEN 'doctor_inbound' THEN 2
            WHEN 'offer_teaser_sent' THEN 3
            WHEN 'offer_made' THEN 4
            WHEN 'offer_declined' THEN 5
            WHEN 'offer_accepted' THEN 6
            WHEN 'handoff_created' THEN 7
            WHEN 'shift_completed' THEN 8
            ELSE 9
        END;
END;
$$;

COMMENT ON FUNCTION count_business_events IS 'Sprint 17: Conta eventos de negócio para funil';
```

2. **Criar função de taxas de conversão**:

```sql
-- Função para calcular taxas de conversão
CREATE OR REPLACE FUNCTION get_funnel_rates(
    p_hours INT DEFAULT 24,
    p_hospital_id UUID DEFAULT NULL
)
RETURNS TABLE (
    metric_name TEXT,
    numerator BIGINT,
    denominator BIGINT,
    rate NUMERIC(5,2)
)
LANGUAGE plpgsql AS $$
DECLARE
    v_outbound BIGINT;
    v_inbound BIGINT;
    v_offer_made BIGINT;
    v_accepted BIGINT;
    v_completed BIGINT;
BEGIN
    -- Contar cada tipo
    SELECT COUNT(*) INTO v_outbound
    FROM business_events
    WHERE event_type = 'doctor_outbound'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_inbound
    FROM business_events
    WHERE event_type = 'doctor_inbound'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_offer_made
    FROM business_events
    WHERE event_type = 'offer_made'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_accepted
    FROM business_events
    WHERE event_type = 'offer_accepted'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    SELECT COUNT(*) INTO v_completed
    FROM business_events
    WHERE event_type = 'shift_completed'
      AND ts >= NOW() - (p_hours || ' hours')::INTERVAL
      AND (p_hospital_id IS NULL OR hospital_id = p_hospital_id);

    -- Retornar taxas
    RETURN QUERY SELECT
        'response_rate'::TEXT,
        v_inbound,
        v_outbound,
        CASE WHEN v_outbound > 0
            THEN ROUND((v_inbound::NUMERIC / v_outbound) * 100, 2)
            ELSE 0
        END;

    RETURN QUERY SELECT
        'conversion_rate'::TEXT,
        v_accepted,
        v_offer_made,
        CASE WHEN v_offer_made > 0
            THEN ROUND((v_accepted::NUMERIC / v_offer_made) * 100, 2)
            ELSE 0
        END;

    RETURN QUERY SELECT
        'completion_rate'::TEXT,
        v_completed,
        v_accepted,
        CASE WHEN v_accepted > 0
            THEN ROUND((v_completed::NUMERIC / v_accepted) * 100, 2)
            ELSE 0
        END;

    RETURN QUERY SELECT
        'overall_success'::TEXT,
        v_completed,
        v_outbound,
        CASE WHEN v_outbound > 0
            THEN ROUND((v_completed::NUMERIC / v_outbound) * 100, 2)
            ELSE 0
        END;
END;
$$;

COMMENT ON FUNCTION get_funnel_rates IS 'Sprint 17: Calcula taxas de conversão do funil';
```

### DoD

- [ ] Função `count_business_events` criada
- [ ] Função `get_funnel_rates` criada
- [ ] Suporte a filtro por hospital_id
- [ ] Suporte a janela de tempo variável
- [ ] Ordenação lógica do funil

---

## Story 6.2: Repository Python para Funil

### Objetivo
Criar repository Python que usa as funções SQL.

### Tarefas

1. **Criar módulo de métricas**:

```python
# app/services/business_events/metrics.py

import logging
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


@dataclass
class FunnelMetrics:
    """Métricas de funil."""
    period_hours: int
    hospital_id: Optional[str]

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
            "count_business_events",
            {"p_hours": hours, "p_hospital_id": hospital_id}
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
            metrics.conversion_rate = round(
                (metrics.offer_accepted / metrics.offer_made) * 100, 2
            )

        if metrics.offer_accepted > 0:
            metrics.completion_rate = round(
                (metrics.shift_completed / metrics.offer_accepted) * 100, 2
            )

        return metrics

    except Exception as e:
        logger.error(f"Erro ao obter métricas de funil: {e}")
        return metrics


async def get_funnel_by_hospital(hours: int = 24) -> list[dict]:
    """
    Obtém funil segmentado por hospital.

    Args:
        hours: Janela de tempo

    Returns:
        Lista de métricas por hospital
    """
    try:
        # Buscar hospitais únicos com eventos
        since = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        response = (
            supabase.table("business_events")
            .select("hospital_id")
            .gte("ts", since)
            .not_.is_("hospital_id", "null")
            .execute()
        )

        # Dedupe hospitais
        hospital_ids = list(set(
            row["hospital_id"] for row in response.data or []
        ))

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
) -> list[dict]:
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
        end = datetime.utcnow() - timedelta(days=i)
        start = end - timedelta(days=1)

        # Para simplificar, usamos a função de horas
        # Cada dia = 24 horas atrás do ponto
        # Isso é aproximado, mas funciona para tendências

        try:
            since = start.isoformat()
            until = end.isoformat()

            # Query manual para período específico
            response = (
                supabase.table("business_events")
                .select("event_type")
                .gte("ts", since)
                .lt("ts", until)
            )

            if hospital_id:
                response = response.eq("hospital_id", hospital_id)

            data = response.execute().data or []

            # Contar por tipo
            counts = {}
            for row in data:
                event_type = row["event_type"]
                counts[event_type] = counts.get(event_type, 0) + 1

            results.append({
                "date": end.strftime("%Y-%m-%d"),
                "counts": counts,
            })

        except Exception as e:
            logger.error(f"Erro ao obter tendência dia {i}: {e}")
            continue

    return list(reversed(results))  # Ordem cronológica
```

### DoD

- [ ] `get_funnel_metrics` implementado
- [ ] `get_funnel_by_hospital` implementado
- [ ] `get_funnel_trend` implementado
- [ ] Usa funções SQL quando disponível
- [ ] Fallback para queries manuais

---

## Story 6.3: Endpoint de Métricas

### Objetivo
Expor métricas de funil via API REST.

### Tarefas

1. **Criar endpoint**:

```python
# app/api/routes/metricas.py

from fastapi import APIRouter, Query
from typing import Optional

from app.services.business_events.metrics import (
    get_funnel_metrics,
    get_funnel_by_hospital,
    get_funnel_trend,
)

router = APIRouter(prefix="/metricas", tags=["Métricas"])


@router.get("/funil")
async def funil_geral(
    hours: int = Query(24, ge=1, le=720),  # Max 30 dias
    hospital_id: Optional[str] = None,
):
    """
    Retorna métricas de funil.

    - **hours**: Janela de tempo em horas (default 24)
    - **hospital_id**: Filtrar por hospital (opcional)
    """
    metrics = await get_funnel_metrics(hours=hours, hospital_id=hospital_id)
    return metrics.to_dict()


@router.get("/funil/hospitais")
async def funil_por_hospital(
    hours: int = Query(24, ge=1, le=720),
):
    """
    Retorna métricas de funil por hospital.

    - **hours**: Janela de tempo em horas (default 24)
    """
    return await get_funnel_by_hospital(hours=hours)


@router.get("/funil/tendencia")
async def funil_tendencia(
    days: int = Query(7, ge=1, le=30),
    hospital_id: Optional[str] = None,
):
    """
    Retorna tendência do funil nos últimos dias.

    - **days**: Número de dias (default 7)
    - **hospital_id**: Filtrar por hospital (opcional)
    """
    return await get_funnel_trend(days=days, hospital_id=hospital_id)
```

### DoD

- [ ] Endpoint `/metricas/funil` funcionando
- [ ] Endpoint `/metricas/funil/hospitais` funcionando
- [ ] Endpoint `/metricas/funil/tendencia` funcionando
- [ ] Validação de parâmetros
- [ ] Documentação OpenAPI

---

## Story 6.4: Testes de Métricas

### Objetivo
Garantir que as queries de funil funcionam corretamente.

### Testes

```python
# tests/business_events/test_metrics.py

import pytest
from unittest.mock import patch, MagicMock

from app.services.business_events.metrics import (
    get_funnel_metrics,
    FunnelMetrics,
)


class TestGetFunnelMetrics:
    """Testes para métricas de funil."""

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_calcula_taxas_corretamente(self, mock_supabase):
        """Calcula taxas de conversão."""
        mock_response = MagicMock()
        mock_response.data = [
            {"event_type": "doctor_outbound", "count": 100},
            {"event_type": "doctor_inbound", "count": 30},
            {"event_type": "offer_made", "count": 20},
            {"event_type": "offer_accepted", "count": 10},
            {"event_type": "shift_completed", "count": 8},
        ]
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        metrics = await get_funnel_metrics(hours=24)

        assert metrics.doctor_outbound == 100
        assert metrics.doctor_inbound == 30
        assert metrics.response_rate == 30.0  # 30/100 * 100
        assert metrics.conversion_rate == 50.0  # 10/20 * 100
        assert metrics.completion_rate == 80.0  # 8/10 * 100
        assert metrics.overall_success == 8.0  # 8/100 * 100

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_trata_divisao_por_zero(self, mock_supabase):
        """Não divide por zero."""
        mock_response = MagicMock()
        mock_response.data = []  # Sem eventos
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        metrics = await get_funnel_metrics(hours=24)

        assert metrics.response_rate == 0.0
        assert metrics.conversion_rate == 0.0
        assert metrics.completion_rate == 0.0
        assert metrics.overall_success == 0.0

    @pytest.mark.asyncio
    @patch("app.services.business_events.metrics.supabase")
    async def test_filtra_por_hospital(self, mock_supabase):
        """Passa hospital_id para a função SQL."""
        mock_response = MagicMock()
        mock_response.data = []
        mock_supabase.rpc.return_value.execute.return_value = mock_response

        await get_funnel_metrics(hours=24, hospital_id="hospital-123")

        mock_supabase.rpc.assert_called_with(
            "count_business_events",
            {"p_hours": 24, "p_hospital_id": "hospital-123"}
        )


class TestFunnelMetricsToDict:
    """Testes para serialização."""

    def test_serializa_corretamente(self):
        """Serializa para dict."""
        metrics = FunnelMetrics(
            period_hours=24,
            hospital_id=None,
            doctor_outbound=100,
            doctor_inbound=30,
            response_rate=30.0,
        )

        result = metrics.to_dict()

        assert result["period_hours"] == 24
        assert result["counts"]["doctor_outbound"] == 100
        assert result["rates"]["response_rate"] == 30.0
```

### DoD

- [ ] Testes para cálculo de taxas
- [ ] Testes para divisão por zero
- [ ] Testes para filtro por hospital
- [ ] Testes de serialização
- [ ] Cobertura > 80%

---

## Checklist do Épico

- [ ] **S17.E06.1** - Funções SQL de agregação
- [ ] **S17.E06.2** - Repository Python
- [ ] **S17.E06.3** - Endpoints REST
- [ ] **S17.E06.4** - Testes passando
- [ ] Funil mostra todas as etapas
- [ ] Taxas calculadas corretamente
- [ ] Suporte a segmentação por hospital
- [ ] Suporte a tendências temporais
