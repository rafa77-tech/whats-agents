# Epic 10: Auditoria de Integridade (Event Coverage)

## Objetivo

Criar auditoria que prova **expectativas deterministicas por fonte**, nao apenas contagem de eventos. Cada camada do sistema tem suas garantias e a auditoria valida cada uma.

## Contexto

### O Problema

Nao basta contar eventos. Precisamos validar:
- **Pipeline** gera `doctor_inbound` para toda mensagem inbound?
- **Agente** gera `doctor_outbound` + `policy_effect.message_sent` para toda saida?
- **DB Trigger** gera evento para toda transicao de status?

### Fontes e Expectativas Deterministicas

| Fonte | Expectativa | Evento Esperado |
|-------|-------------|-----------------|
| Pipeline (inbound) | Toda msg entrada em `interacoes` | `business_event.doctor_inbound` |
| Agente (outbound) | Toda msg saida enviada | `business_event.doctor_outbound` |
| Policy Engine | Toda decisao de envio | `policy_event.message_sent` |
| DB Trigger | Status `reservada` | `business_event.offer_accepted` |
| DB Trigger | Status `pendente_confirmacao` | `business_event.shift_pending_confirmation` |
| DB Trigger | Status `realizada` | `business_event.shift_completed` |
| DB Trigger | Status `cancelada` | `business_event.shift_cancelled` |
| Handoff | Transicao para humano | `business_event.handoff_started` |

---

## Story 10.1: Queries de Cobertura por Fonte

### Objetivo
Validar que cada fonte gera os eventos esperados.

### Tarefas

1. **Query: Pipeline → doctor_inbound**

```sql
-- Toda mensagem inbound no periodo deve ter business_event.doctor_inbound
-- Fonte: pipeline de processamento

CREATE OR REPLACE FUNCTION audit_pipeline_inbound_coverage(
    p_start TIMESTAMPTZ,
    p_end TIMESTAMPTZ
)
RETURNS TABLE (
    source TEXT,
    expected_count BIGINT,
    actual_count BIGINT,
    coverage_pct NUMERIC(5,2),
    missing_ids UUID[]
) AS $$
DECLARE
    v_expected BIGINT;
    v_actual BIGINT;
    v_missing UUID[];
BEGIN
    -- Contar interacoes de entrada no periodo
    SELECT COUNT(*) INTO v_expected
    FROM interacoes
    WHERE direcao = 'entrada'
      AND created_at >= p_start
      AND created_at < p_end;

    -- Contar eventos doctor_inbound no periodo
    SELECT COUNT(*) INTO v_actual
    FROM business_events
    WHERE event_type = 'doctor_inbound'
      AND ts >= p_start
      AND ts < p_end;

    -- Identificar IDs faltantes (interacoes sem evento)
    SELECT ARRAY_AGG(i.id) INTO v_missing
    FROM interacoes i
    LEFT JOIN business_events be ON
        be.event_type = 'doctor_inbound'
        AND be.event_props->>'interacao_id' = i.id::text
        AND be.ts >= p_start AND be.ts < p_end
    WHERE i.direcao = 'entrada'
      AND i.created_at >= p_start
      AND i.created_at < p_end
      AND be.id IS NULL
    LIMIT 100;  -- Limitar para nao explodir

    RETURN QUERY SELECT
        'pipeline_inbound'::TEXT,
        v_expected,
        v_actual,
        CASE WHEN v_expected = 0 THEN 100.0
             ELSE ROUND((v_actual::numeric / v_expected) * 100, 2)
        END,
        COALESCE(v_missing, ARRAY[]::UUID[]);
END;
$$ LANGUAGE plpgsql;
```

2. **Query: Agente → doctor_outbound + policy_effect**

```sql
-- Todo outbound enviado deve ter doctor_outbound E policy_effect.message_sent
-- Duas camadas diferentes que devem reconciliar

CREATE OR REPLACE FUNCTION audit_outbound_coverage(
    p_start TIMESTAMPTZ,
    p_end TIMESTAMPTZ
)
RETURNS TABLE (
    source TEXT,
    expected_count BIGINT,
    actual_count BIGINT,
    coverage_pct NUMERIC(5,2),
    layer TEXT,
    notes TEXT
) AS $$
BEGIN
    -- Layer 1: interacoes saida → doctor_outbound (business_events)
    RETURN QUERY
    WITH outbound_msgs AS (
        SELECT COUNT(*) as cnt FROM interacoes
        WHERE direcao = 'saida' AND created_at >= p_start AND created_at < p_end
    ),
    outbound_events AS (
        SELECT COUNT(*) as cnt FROM business_events
        WHERE event_type = 'doctor_outbound' AND ts >= p_start AND ts < p_end
    )
    SELECT
        'agente_outbound'::TEXT,
        o.cnt,
        e.cnt,
        CASE WHEN o.cnt = 0 THEN 100.0 ELSE ROUND((e.cnt::numeric / o.cnt) * 100, 2) END,
        'business_events'::TEXT,
        'doctor_outbound para cada saida'::TEXT
    FROM outbound_msgs o, outbound_events e;

    -- Layer 2: policy_events com effect = message_sent
    RETURN QUERY
    WITH outbound_msgs AS (
        SELECT COUNT(*) as cnt FROM interacoes
        WHERE direcao = 'saida' AND created_at >= p_start AND created_at < p_end
    ),
    policy_events AS (
        SELECT COUNT(*) as cnt FROM policy_events
        WHERE effect = 'message_sent' AND ts >= p_start AND ts < p_end
    )
    SELECT
        'agente_outbound'::TEXT,
        o.cnt,
        p.cnt,
        CASE WHEN o.cnt = 0 THEN 100.0 ELSE ROUND((p.cnt::numeric / o.cnt) * 100, 2) END,
        'policy_events'::TEXT,
        'policy_effect.message_sent para cada saida'::TEXT
    FROM outbound_msgs o, policy_events p;
END;
$$ LANGUAGE plpgsql;
```

3. **Query: DB Trigger → Eventos de Status**

```sql
-- Toda transicao de status deve gerar evento correspondente
-- Fonte: DB trigger (ou codigo de atualizacao)

CREATE OR REPLACE FUNCTION audit_status_transition_coverage(
    p_start TIMESTAMPTZ,
    p_end TIMESTAMPTZ
)
RETURNS TABLE (
    status_from TEXT,
    status_to TEXT,
    expected_event TEXT,
    db_transitions BIGINT,
    events_found BIGINT,
    coverage_pct NUMERIC(5,2),
    missing_vaga_ids UUID[]
) AS $$
BEGIN
    -- Transicao: * → reservada
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id, v.updated_at
        FROM vagas v
        WHERE v.status = 'reservada'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'offer_accepted'
          AND ts >= p_start AND ts < p_end
    ),
    missing AS (
        SELECT ARRAY_AGG(t.id) as ids
        FROM transitions t
        LEFT JOIN events e ON e.vaga_id = t.id
        WHERE e.vaga_id IS NULL
        LIMIT 50
    )
    SELECT
        '*'::TEXT,
        'reservada'::TEXT,
        'offer_accepted'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        COALESCE((SELECT ids FROM missing), ARRAY[]::UUID[]);

    -- Transicao: reservada → pendente_confirmacao
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id FROM vagas v
        WHERE v.status = 'pendente_confirmacao'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'shift_pending_confirmation'
          AND ts >= p_start AND ts < p_end
    )
    SELECT
        'reservada'::TEXT,
        'pendente_confirmacao'::TEXT,
        'shift_pending_confirmation'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        ARRAY[]::UUID[];

    -- Transicao: * → realizada
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id FROM vagas v
        WHERE v.status = 'realizada'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'shift_completed'
          AND ts >= p_start AND ts < p_end
    )
    SELECT
        '*'::TEXT,
        'realizada'::TEXT,
        'shift_completed'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        ARRAY[]::UUID[];

    -- Transicao: * → cancelada
    RETURN QUERY
    WITH transitions AS (
        SELECT v.id FROM vagas v
        WHERE v.status = 'cancelada'
          AND v.updated_at >= p_start AND v.updated_at < p_end
    ),
    events AS (
        SELECT DISTINCT vaga_id FROM business_events
        WHERE event_type = 'shift_cancelled'
          AND ts >= p_start AND ts < p_end
    )
    SELECT
        '*'::TEXT,
        'cancelada'::TEXT,
        'shift_cancelled'::TEXT,
        (SELECT COUNT(*) FROM transitions),
        (SELECT COUNT(*) FROM events),
        CASE WHEN (SELECT COUNT(*) FROM transitions) = 0 THEN 100.0
             ELSE ROUND(((SELECT COUNT(*) FROM events)::numeric / (SELECT COUNT(*) FROM transitions)) * 100, 2)
        END,
        ARRAY[]::UUID[];
END;
$$ LANGUAGE plpgsql;
```

### DoD

- [ ] Query de cobertura pipeline inbound funcionando
- [ ] Query de cobertura outbound (2 layers) funcionando
- [ ] Query de transicoes de status funcionando
- [ ] IDs faltantes identificados para debug

---

## Story 10.2: Queries de Integridade do Funil

### Objetivo
Detectar anomalias na sequencia de eventos (invariantes quebradas).

### Invariantes do Funil

| Invariante | Descricao | Anomalia se Violada |
|------------|-----------|---------------------|
| offer_accepted → offer_made | Todo aceite precisa de oferta previa | `aceite_sem_oferta` |
| offer_made → vaga_id | Oferta especifica precisa de vaga | `oferta_sem_vaga_id` |
| shift_completed → offer_accepted | Conclusao precisa de aceite | `completado_sem_aceite` |
| handoff_started → conversa ativa | Handoff precisa de conversa | `handoff_orfao` |

### Tarefas

```sql
CREATE OR REPLACE FUNCTION get_funnel_invariant_violations(
    p_days INT DEFAULT 7
)
RETURNS TABLE (
    invariant_name TEXT,
    violation_type TEXT,
    event_id UUID,
    vaga_id UUID,
    cliente_id UUID,
    event_ts TIMESTAMPTZ,
    details JSONB
) AS $$
BEGIN
    -- Invariante 1: offer_accepted deve ter offer_made previo
    RETURN QUERY
    SELECT
        'offer_accepted_requires_offer_made'::TEXT,
        'aceite_sem_oferta'::TEXT,
        a.id,
        a.vaga_id,
        a.cliente_id,
        a.ts,
        jsonb_build_object(
            'event_type', a.event_type,
            'vaga_id', a.vaga_id
        )
    FROM business_events a
    WHERE a.event_type = 'offer_accepted'
      AND a.ts >= now() - (p_days || ' days')::interval
      AND a.vaga_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM business_events o
          WHERE o.event_type = 'offer_made'
            AND o.vaga_id = a.vaga_id
            AND o.cliente_id = a.cliente_id
            AND o.ts < a.ts
      );

    -- Invariante 2: offer_made especifico deve ter vaga_id
    RETURN QUERY
    SELECT
        'offer_made_requires_vaga_id'::TEXT,
        'oferta_sem_vaga_id'::TEXT,
        id,
        NULL::UUID,
        cliente_id,
        ts,
        jsonb_build_object(
            'event_props', event_props,
            'note', 'offer_made sem vaga_id - deveria ser offer_teaser_sent?'
        )
    FROM business_events
    WHERE event_type = 'offer_made'
      AND vaga_id IS NULL
      AND ts >= now() - (p_days || ' days')::interval;

    -- Invariante 3: shift_completed deve ter offer_accepted previo
    RETURN QUERY
    SELECT
        'shift_completed_requires_accepted'::TEXT,
        'completado_sem_aceite'::TEXT,
        c.id,
        c.vaga_id,
        c.cliente_id,
        c.ts,
        jsonb_build_object('vaga_id', c.vaga_id)
    FROM business_events c
    WHERE c.event_type = 'shift_completed'
      AND c.ts >= now() - (p_days || ' days')::interval
      AND c.vaga_id IS NOT NULL
      AND NOT EXISTS (
          SELECT 1 FROM business_events a
          WHERE a.event_type = 'offer_accepted'
            AND a.vaga_id = c.vaga_id
            AND a.ts < c.ts
      );

    -- Invariante 4: handoff_started deve ter conversa
    RETURN QUERY
    SELECT
        'handoff_requires_conversation'::TEXT,
        'handoff_orfao'::TEXT,
        h.id,
        NULL::UUID,
        h.cliente_id,
        h.ts,
        jsonb_build_object('conversa_id', h.event_props->>'conversa_id')
    FROM business_events h
    WHERE h.event_type = 'handoff_started'
      AND h.ts >= now() - (p_days || ' days')::interval
      AND NOT EXISTS (
          SELECT 1 FROM conversations c
          WHERE c.cliente_id = h.cliente_id
            AND c.status = 'active'
      );
END;
$$ LANGUAGE plpgsql;
```

### DoD

- [ ] Funcao `get_funnel_invariant_violations` criada
- [ ] Todas as 4 invariantes verificadas
- [ ] Detalhes para debug incluidos

---

## Story 10.3: Servico Python de Auditoria

### Objetivo
Servico que executa todas as auditorias e expoe resultados.

```python
# app/services/business_events/audit.py

"""
Auditoria de cobertura de eventos por fonte.

Sprint 18 - Data Integrity
Audita expectativas DETERMINISTICAS, nao contagens abstratas.
"""
import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

from app.services.supabase import supabase

logger = logging.getLogger(__name__)


class CoverageSource(Enum):
    """Fonte de eventos."""
    PIPELINE_INBOUND = "pipeline_inbound"
    AGENTE_OUTBOUND = "agente_outbound"
    DB_TRIGGER_STATUS = "db_trigger_status"
    HANDOFF = "handoff"


class CoverageStatus(Enum):
    """Status da cobertura."""
    OK = "ok"           # >= 98%
    WARNING = "warning"  # >= 90%
    CRITICAL = "critical"  # < 90%


@dataclass
class SourceCoverage:
    """Cobertura de uma fonte especifica."""
    source: CoverageSource
    layer: str  # ex: "business_events", "policy_events"
    expectation: str  # O que deveria acontecer
    expected_count: int
    actual_count: int
    coverage_pct: float
    status: CoverageStatus
    missing_ids: List[str] = field(default_factory=list)
    notes: Optional[str] = None

    @classmethod
    def from_row(cls, row: dict, source: CoverageSource) -> "SourceCoverage":
        """Cria a partir de row do banco."""
        coverage = row.get("coverage_pct", 0)
        status = (
            CoverageStatus.OK if coverage >= 98 else
            CoverageStatus.WARNING if coverage >= 90 else
            CoverageStatus.CRITICAL
        )
        return cls(
            source=source,
            layer=row.get("layer", "business_events"),
            expectation=row.get("notes", ""),
            expected_count=row.get("expected_count", 0),
            actual_count=row.get("actual_count", 0),
            coverage_pct=coverage,
            status=status,
            missing_ids=[str(x) for x in row.get("missing_ids", []) or []],
            notes=row.get("notes"),
        )


@dataclass
class InvariantViolation:
    """Violacao de invariante do funil."""
    invariant_name: str
    violation_type: str
    event_id: str
    vaga_id: Optional[str]
    cliente_id: Optional[str]
    event_ts: datetime
    details: dict


@dataclass
class AuditResult:
    """Resultado completo da auditoria."""
    timestamp: datetime
    period_start: datetime
    period_end: datetime
    overall_status: CoverageStatus
    coverage_by_source: List[SourceCoverage]
    invariant_violations: List[InvariantViolation]
    summary: Dict[str, int]

    def to_dict(self) -> dict:
        """Serializa para JSON."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat(),
            },
            "overall_status": self.overall_status.value,
            "coverage": [
                {
                    "source": c.source.value,
                    "layer": c.layer,
                    "expectation": c.expectation,
                    "expected": c.expected_count,
                    "actual": c.actual_count,
                    "coverage_pct": c.coverage_pct,
                    "status": c.status.value,
                    "missing_sample": c.missing_ids[:5],  # Amostra
                }
                for c in self.coverage_by_source
            ],
            "violations": {
                "count": len(self.invariant_violations),
                "by_type": self._group_violations(),
                "sample": [
                    {
                        "type": v.violation_type,
                        "event_id": v.event_id,
                        "vaga_id": v.vaga_id,
                    }
                    for v in self.invariant_violations[:10]
                ],
            },
            "summary": self.summary,
        }

    def _group_violations(self) -> dict:
        """Agrupa violacoes por tipo."""
        grouped = {}
        for v in self.invariant_violations:
            grouped[v.violation_type] = grouped.get(v.violation_type, 0) + 1
        return grouped


async def audit_pipeline_inbound(
    start: datetime,
    end: datetime
) -> List[SourceCoverage]:
    """Audita cobertura do pipeline inbound."""
    try:
        response = supabase.rpc(
            "audit_pipeline_inbound_coverage",
            {"p_start": start.isoformat(), "p_end": end.isoformat()}
        ).execute()

        return [
            SourceCoverage.from_row(row, CoverageSource.PIPELINE_INBOUND)
            for row in response.data or []
        ]
    except Exception as e:
        logger.error(f"Erro ao auditar pipeline inbound: {e}")
        return []


async def audit_outbound_coverage(
    start: datetime,
    end: datetime
) -> List[SourceCoverage]:
    """Audita cobertura de outbound (2 layers)."""
    try:
        response = supabase.rpc(
            "audit_outbound_coverage",
            {"p_start": start.isoformat(), "p_end": end.isoformat()}
        ).execute()

        return [
            SourceCoverage.from_row(row, CoverageSource.AGENTE_OUTBOUND)
            for row in response.data or []
        ]
    except Exception as e:
        logger.error(f"Erro ao auditar outbound: {e}")
        return []


async def audit_status_transitions(
    start: datetime,
    end: datetime
) -> List[SourceCoverage]:
    """Audita cobertura de transicoes de status."""
    try:
        response = supabase.rpc(
            "audit_status_transition_coverage",
            {"p_start": start.isoformat(), "p_end": end.isoformat()}
        ).execute()

        coverages = []
        for row in response.data or []:
            coverage = row.get("coverage_pct", 0)
            status = (
                CoverageStatus.OK if coverage >= 98 else
                CoverageStatus.WARNING if coverage >= 90 else
                CoverageStatus.CRITICAL
            )
            coverages.append(SourceCoverage(
                source=CoverageSource.DB_TRIGGER_STATUS,
                layer="business_events",
                expectation=f"{row['status_from']} → {row['status_to']} gera {row['expected_event']}",
                expected_count=row["db_transitions"],
                actual_count=row["events_found"],
                coverage_pct=coverage,
                status=status,
                missing_ids=[str(x) for x in row.get("missing_vaga_ids", []) or []],
            ))
        return coverages
    except Exception as e:
        logger.error(f"Erro ao auditar transicoes: {e}")
        return []


async def get_invariant_violations(days: int = 7) -> List[InvariantViolation]:
    """Obtem violacoes de invariantes do funil."""
    try:
        response = supabase.rpc(
            "get_funnel_invariant_violations",
            {"p_days": days}
        ).execute()

        violations = []
        for row in response.data or []:
            violations.append(InvariantViolation(
                invariant_name=row["invariant_name"],
                violation_type=row["violation_type"],
                event_id=str(row["event_id"]),
                vaga_id=str(row["vaga_id"]) if row.get("vaga_id") else None,
                cliente_id=str(row["cliente_id"]) if row.get("cliente_id") else None,
                event_ts=datetime.fromisoformat(
                    row["event_ts"].replace("Z", "+00:00")
                ),
                details=row.get("details", {}),
            ))
        return violations
    except Exception as e:
        logger.error(f"Erro ao obter violacoes: {e}")
        return []


async def run_full_audit(hours: int = 24) -> AuditResult:
    """
    Executa auditoria completa de cobertura.

    Args:
        hours: Janela de tempo em horas

    Returns:
        AuditResult com todas as metricas
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)

    # Coletar todas as coberturas
    all_coverage: List[SourceCoverage] = []

    # 1. Pipeline inbound
    inbound = await audit_pipeline_inbound(start, now)
    all_coverage.extend(inbound)

    # 2. Outbound (2 layers)
    outbound = await audit_outbound_coverage(start, now)
    all_coverage.extend(outbound)

    # 3. Transicoes de status
    transitions = await audit_status_transitions(start, now)
    all_coverage.extend(transitions)

    # 4. Violacoes de invariantes
    violations = await get_invariant_violations(days=7)

    # Calcular status geral
    has_critical = any(c.status == CoverageStatus.CRITICAL for c in all_coverage)
    has_warning = any(c.status == CoverageStatus.WARNING for c in all_coverage)

    if has_critical or len(violations) > 10:
        overall = CoverageStatus.CRITICAL
    elif has_warning or len(violations) > 0:
        overall = CoverageStatus.WARNING
    else:
        overall = CoverageStatus.OK

    # Sumario
    summary = {
        "sources_audited": len(all_coverage),
        "sources_ok": sum(1 for c in all_coverage if c.status == CoverageStatus.OK),
        "sources_warning": sum(1 for c in all_coverage if c.status == CoverageStatus.WARNING),
        "sources_critical": sum(1 for c in all_coverage if c.status == CoverageStatus.CRITICAL),
        "violations_total": len(violations),
    }

    return AuditResult(
        timestamp=now,
        period_start=start,
        period_end=now,
        overall_status=overall,
        coverage_by_source=all_coverage,
        invariant_violations=violations,
        summary=summary,
    )
```

### DoD

- [ ] Servico implementado com auditoria por fonte
- [ ] 3 fontes auditadas: pipeline, agente, db trigger
- [ ] Invariantes do funil verificadas
- [ ] Status calculados (ok/warning/critical)

---

## Story 10.4: Endpoint de Auditoria

```python
# app/api/routes/metricas.py (adicao)

@router.get("/auditoria/cobertura")
async def auditoria_cobertura(
    hours: int = Query(24, ge=1, le=168, description="Janela em horas"),
):
    """
    Retorna auditoria de cobertura de eventos por fonte.

    Valida expectativas deterministicas:
    - Pipeline inbound → doctor_inbound
    - Agente outbound → doctor_outbound + policy_effect.message_sent
    - DB trigger → eventos de transicao de status

    Returns:
        AuditResult com cobertura por fonte e violacoes de invariantes
    """
    from app.services.business_events.audit import run_full_audit
    result = await run_full_audit(hours)
    return result.to_dict()


@router.get("/auditoria/violacoes")
async def auditoria_violacoes(
    days: int = Query(7, ge=1, le=30, description="Janela em dias"),
):
    """
    Retorna violacoes de invariantes do funil.

    Detecta:
    - offer_accepted sem offer_made previo
    - offer_made sem vaga_id
    - shift_completed sem offer_accepted
    - handoff_started sem conversa ativa
    """
    from app.services.business_events.audit import get_invariant_violations
    violations = await get_invariant_violations(days)
    return {
        "count": len(violations),
        "violations": [
            {
                "type": v.violation_type,
                "invariant": v.invariant_name,
                "event_id": v.event_id,
                "vaga_id": v.vaga_id,
                "cliente_id": v.cliente_id,
                "event_ts": v.event_ts.isoformat(),
                "details": v.details,
            }
            for v in violations
        ],
    }
```

### DoD

- [ ] Endpoint `/metricas/auditoria/cobertura` funcionando
- [ ] Endpoint `/metricas/auditoria/violacoes` funcionando
- [ ] Resposta inclui cobertura por fonte
- [ ] Resposta inclui amostra de IDs faltantes

---

## Checklist do Epico

- [ ] **S18.E10.1** - Queries de cobertura por fonte (3 fontes)
- [ ] **S18.E10.2** - Queries de invariantes do funil
- [ ] **S18.E10.3** - Servico Python de auditoria
- [ ] **S18.E10.4** - Endpoints de auditoria
- [ ] Todas as fontes auditadas
- [ ] IDs faltantes identificaveis para debug
- [ ] Status ok/warning/critical calculados
