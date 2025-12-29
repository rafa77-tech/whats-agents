# Epic 11: Reconciliacao DB vs Eventos (Bidirecional)

## Objetivo

Criar job diario que compara **bidirecionalmente**:
1. **DB → Eventos esperados**: Status changes, mensagens, handoffs devem ter evento
2. **Eventos → DB esperado**: `shift_completed` implica `vaga.status = realizada`

## Contexto

### O Problema

Mesmo com boa instrumentacao, podem ocorrer:
- Evento nao emitido por erro de codigo
- Evento perdido por falha de rede
- Trigger DB desabilitado por engano
- Mudanca de status manual sem trigger
- Evento emitido mas DB nao atualizado (bug)

### A Solucao: Reconciliacao Bidirecional

| Direcao | Pergunta | Exemplo |
|---------|----------|---------|
| DB → Eventos | "Vaga reservada gerou offer_accepted?" | Vaga.status=reservada → deve existir offer_accepted |
| Eventos → DB | "offer_accepted tem vaga reservada?" | offer_accepted → vaga.status deve ser reservada |

**Ambas direcoes sao necessarias para detectar todos os buracos.**

---

## Story 11.1: Tabela data_anomalies (Schema Melhorado)

### Objetivo
Criar tabela para historico de anomalias com tracking de recorrencia.

### Schema

```sql
-- Migration: create_data_anomalies_v2
-- Sprint 18 - E11

CREATE TABLE IF NOT EXISTS public.data_anomalies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Classificacao
    anomaly_type TEXT NOT NULL,          -- 'missing_event', 'orphan_event', 'state_mismatch'
    entity_type TEXT NOT NULL,           -- 'vaga', 'cliente', 'conversation', 'business_event'
    entity_id UUID NOT NULL,             -- ID da entidade afetada

    -- Expectativa vs Realidade
    expected TEXT NOT NULL,              -- O que deveria existir/acontecer
    found TEXT,                          -- O que foi encontrado (null = nada)

    -- Tracking de recorrencia
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    occurrence_count INT NOT NULL DEFAULT 1,

    -- Metadados
    severity TEXT NOT NULL DEFAULT 'warning',  -- 'warning', 'critical'
    details JSONB DEFAULT '{}',
    reconciliation_run_id UUID,          -- ID do job que detectou

    -- Resolucao
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by TEXT,
    resolution_notes TEXT,

    -- Audit
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indice unico para deduplicacao (mesma anomalia = atualiza count)
CREATE UNIQUE INDEX idx_data_anomalies_dedup
    ON data_anomalies(anomaly_type, entity_type, entity_id)
    WHERE resolved = FALSE;

-- Indices de consulta
CREATE INDEX idx_data_anomalies_last_seen ON data_anomalies(last_seen_at DESC);
CREATE INDEX idx_data_anomalies_type ON data_anomalies(anomaly_type);
CREATE INDEX idx_data_anomalies_entity ON data_anomalies(entity_type, entity_id);
CREATE INDEX idx_data_anomalies_unresolved ON data_anomalies(resolved) WHERE resolved = FALSE;
CREATE INDEX idx_data_anomalies_severity ON data_anomalies(severity) WHERE resolved = FALSE;

-- RLS
ALTER TABLE data_anomalies ENABLE ROW LEVEL SECURITY;

-- Trigger para updated_at
CREATE OR REPLACE FUNCTION update_data_anomalies_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_data_anomalies_updated_at
    BEFORE UPDATE ON data_anomalies
    FOR EACH ROW
    EXECUTE FUNCTION update_data_anomalies_updated_at();

-- Comentarios
COMMENT ON TABLE data_anomalies IS 'Sprint 18 - E11: Historico de anomalias de dados com tracking de recorrencia';
COMMENT ON COLUMN data_anomalies.expected IS 'O que deveria existir (ex: "evento offer_accepted")';
COMMENT ON COLUMN data_anomalies.found IS 'O que foi encontrado (ex: "nenhum evento" ou "status=aberta")';
COMMENT ON COLUMN data_anomalies.occurrence_count IS 'Quantas vezes essa anomalia foi detectada';
```

### DoD

- [ ] Tabela `data_anomalies` criada com schema melhorado
- [ ] Indice de deduplicacao funcionando
- [ ] Trigger de updated_at funcionando

---

## Story 11.2: Reconciliacao Bidirecional

### Objetivo
Queries que detectam divergencias nas duas direcoes.

### Direcao 1: DB → Eventos Esperados

```sql
-- DB → Eventos: Mudancas de status devem ter eventos correspondentes

CREATE OR REPLACE FUNCTION reconcile_db_to_events(
    p_start TIMESTAMPTZ,
    p_end TIMESTAMPTZ
)
RETURNS TABLE (
    anomaly_type TEXT,
    entity_type TEXT,
    entity_id UUID,
    expected TEXT,
    found TEXT,
    details JSONB
) AS $$
BEGIN
    -- 1. Vaga reservada → offer_accepted
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento offer_accepted'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at,
            'cliente_id', v.cliente_id
        )
    FROM vagas v
    WHERE v.status = 'reservada'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'offer_accepted'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 2. Vaga pendente_confirmacao → shift_pending_confirmation
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento shift_pending_confirmation'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at
        )
    FROM vagas v
    WHERE v.status = 'pendente_confirmacao'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'shift_pending_confirmation'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 3. Vaga realizada → shift_completed
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento shift_completed'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at,
            'realizada_por', v.realizada_por
        )
    FROM vagas v
    WHERE v.status = 'realizada'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'shift_completed'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 4. Vaga cancelada → shift_cancelled
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'vaga'::TEXT,
        v.id,
        'evento shift_cancelled'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'vaga_status', v.status,
            'vaga_updated_at', v.updated_at
        )
    FROM vagas v
    WHERE v.status = 'cancelada'
      AND v.updated_at >= p_start AND v.updated_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'shift_cancelled'
            AND be.vaga_id = v.id
            AND be.ts >= v.updated_at - interval '1 hour'
      );

    -- 5. Handoff criado → handoff_started
    RETURN QUERY
    SELECT
        'missing_event'::TEXT,
        'handoff'::TEXT,
        h.id,
        'evento handoff_started'::TEXT,
        'nenhum evento encontrado'::TEXT,
        jsonb_build_object(
            'conversa_id', h.conversa_id,
            'created_at', h.created_at
        )
    FROM handoffs h
    WHERE h.created_at >= p_start AND h.created_at < p_end
      AND NOT EXISTS (
          SELECT 1 FROM business_events be
          WHERE be.event_type = 'handoff_started'
            AND be.event_props->>'handoff_id' = h.id::text
            AND be.ts >= h.created_at - interval '1 minute'
      );
END;
$$ LANGUAGE plpgsql;
```

### Direcao 2: Eventos → DB Esperado

```sql
-- Eventos → DB: Eventos devem refletir estado no banco

CREATE OR REPLACE FUNCTION reconcile_events_to_db(
    p_start TIMESTAMPTZ,
    p_end TIMESTAMPTZ
)
RETURNS TABLE (
    anomaly_type TEXT,
    entity_type TEXT,
    entity_id UUID,
    expected TEXT,
    found TEXT,
    details JSONB
) AS $$
BEGIN
    -- 1. offer_accepted → vaga deve estar reservada/realizada
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'vaga.status IN (reservada, realizada)'::TEXT,
        COALESCE('vaga.status = ' || v.status, 'vaga nao encontrada')::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'vaga_id', be.vaga_id,
            'event_ts', be.ts,
            'vaga_status', v.status
        )
    FROM business_events be
    LEFT JOIN vagas v ON v.id = be.vaga_id
    WHERE be.event_type = 'offer_accepted'
      AND be.ts >= p_start AND be.ts < p_end
      AND be.vaga_id IS NOT NULL
      AND (v.id IS NULL OR v.status NOT IN ('reservada', 'realizada', 'pendente_confirmacao'));

    -- 2. shift_completed → vaga deve estar realizada
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'vaga.status = realizada'::TEXT,
        COALESCE('vaga.status = ' || v.status, 'vaga nao encontrada')::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'vaga_id', be.vaga_id,
            'event_ts', be.ts,
            'vaga_status', v.status
        )
    FROM business_events be
    LEFT JOIN vagas v ON v.id = be.vaga_id
    WHERE be.event_type = 'shift_completed'
      AND be.ts >= p_start AND be.ts < p_end
      AND be.vaga_id IS NOT NULL
      AND (v.id IS NULL OR v.status != 'realizada');

    -- 3. shift_cancelled → vaga deve estar cancelada
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'vaga.status = cancelada'::TEXT,
        COALESCE('vaga.status = ' || v.status, 'vaga nao encontrada')::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'vaga_id', be.vaga_id,
            'event_ts', be.ts,
            'vaga_status', v.status
        )
    FROM business_events be
    LEFT JOIN vagas v ON v.id = be.vaga_id
    WHERE be.event_type = 'shift_cancelled'
      AND be.ts >= p_start AND be.ts < p_end
      AND be.vaga_id IS NOT NULL
      AND (v.id IS NULL OR v.status != 'cancelada');

    -- 4. handoff_resolved → handoff deve estar resolvido
    RETURN QUERY
    SELECT
        'state_mismatch'::TEXT,
        'business_event'::TEXT,
        be.id,
        'handoff.resolved_at IS NOT NULL'::TEXT,
        'handoff nao resolvido ou nao encontrado'::TEXT,
        jsonb_build_object(
            'event_type', be.event_type,
            'handoff_id', be.event_props->>'handoff_id',
            'event_ts', be.ts
        )
    FROM business_events be
    WHERE be.event_type = 'handoff_resolved'
      AND be.ts >= p_start AND be.ts < p_end
      AND NOT EXISTS (
          SELECT 1 FROM handoffs h
          WHERE h.id::text = be.event_props->>'handoff_id'
            AND h.resolved_at IS NOT NULL
      );
END;
$$ LANGUAGE plpgsql;
```

### Funcao Unificada

```sql
-- Reconciliacao completa (ambas direcoes)

CREATE OR REPLACE FUNCTION reconcile_all(
    p_hours INT DEFAULT 24
)
RETURNS TABLE (
    direction TEXT,
    anomaly_type TEXT,
    entity_type TEXT,
    entity_id UUID,
    expected TEXT,
    found TEXT,
    details JSONB
) AS $$
DECLARE
    v_start TIMESTAMPTZ;
    v_end TIMESTAMPTZ;
BEGIN
    v_end := now();
    v_start := v_end - (p_hours || ' hours')::interval;

    -- DB → Eventos
    RETURN QUERY
    SELECT
        'db_to_events'::TEXT,
        r.anomaly_type,
        r.entity_type,
        r.entity_id,
        r.expected,
        r.found,
        r.details
    FROM reconcile_db_to_events(v_start, v_end) r;

    -- Eventos → DB
    RETURN QUERY
    SELECT
        'events_to_db'::TEXT,
        r.anomaly_type,
        r.entity_type,
        r.entity_id,
        r.expected,
        r.found,
        r.details
    FROM reconcile_events_to_db(v_start, v_end) r;
END;
$$ LANGUAGE plpgsql;
```

### DoD

- [ ] Funcao `reconcile_db_to_events` criada
- [ ] Funcao `reconcile_events_to_db` criada
- [ ] Funcao `reconcile_all` unificadora
- [ ] Ambas direcoes cobrem os casos principais

---

## Story 11.3: Servico de Reconciliacao com Deduplicacao

### Objetivo
Servico que persiste anomalias com tracking de recorrencia.

```python
# app/services/business_events/reconciliation.py

"""
Reconciliacao bidirecional DB vs Eventos.

Sprint 18 - Data Integrity
Detecta divergencias nas duas direcoes:
- DB → Eventos esperados
- Eventos → DB esperado
"""
import logging
from datetime import datetime, timezone
from typing import List, Optional
from dataclasses import dataclass
from uuid import uuid4

from app.services.supabase import supabase
from app.services.slack import enviar_slack

logger = logging.getLogger(__name__)


@dataclass
class DataAnomaly:
    """Anomalia de dados detectada."""
    direction: str              # 'db_to_events' ou 'events_to_db'
    anomaly_type: str           # 'missing_event', 'state_mismatch', etc
    entity_type: str            # 'vaga', 'cliente', 'business_event'
    entity_id: str
    expected: str               # O que deveria existir
    found: Optional[str]        # O que foi encontrado
    details: dict
    severity: str = "warning"

    def to_insert_dict(self, run_id: str) -> dict:
        """Converte para insert no banco."""
        return {
            "anomaly_type": self.anomaly_type,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "expected": self.expected,
            "found": self.found,
            "severity": self.severity,
            "details": {**self.details, "direction": self.direction},
            "reconciliation_run_id": run_id,
        }


def _determine_severity(anomaly_type: str, entity_type: str) -> str:
    """Determina severidade da anomalia."""
    critical_patterns = [
        ("state_mismatch", "business_event"),  # Evento sem reflexo no DB
        ("missing_event", "vaga"),             # Vaga sem evento
    ]
    for pattern_type, pattern_entity in critical_patterns:
        if anomaly_type == pattern_type and entity_type == pattern_entity:
            return "critical"
    return "warning"


async def run_reconciliation(hours: int = 24) -> List[DataAnomaly]:
    """
    Executa reconciliacao bidirecional.

    Args:
        hours: Janela de tempo

    Returns:
        Lista de anomalias detectadas
    """
    try:
        response = supabase.rpc(
            "reconcile_all",
            {"p_hours": hours}
        ).execute()

        anomalies = []
        for row in response.data or []:
            anomaly = DataAnomaly(
                direction=row["direction"],
                anomaly_type=row["anomaly_type"],
                entity_type=row["entity_type"],
                entity_id=str(row["entity_id"]),
                expected=row["expected"],
                found=row.get("found"),
                details=row.get("details", {}),
            )
            anomaly.severity = _determine_severity(
                anomaly.anomaly_type,
                anomaly.entity_type
            )
            anomalies.append(anomaly)

        return anomalies

    except Exception as e:
        logger.error(f"Erro na reconciliacao: {e}")
        return []


async def persist_anomalies_with_dedup(
    anomalies: List[DataAnomaly],
    run_id: str
) -> dict:
    """
    Persiste anomalias com deduplicacao.

    Anomalias ja existentes (mesma entidade/tipo) tem count incrementado.
    Novas anomalias sao inseridas.

    Returns:
        {"inserted": N, "updated": M}
    """
    if not anomalies:
        return {"inserted": 0, "updated": 0}

    inserted = 0
    updated = 0

    for anomaly in anomalies:
        try:
            # Tentar update primeiro (dedup)
            update_response = supabase.table("data_anomalies").update({
                "last_seen_at": datetime.now(timezone.utc).isoformat(),
                "occurrence_count": supabase.sql("occurrence_count + 1"),
                "details": anomaly.details,
                "reconciliation_run_id": run_id,
            }).eq("anomaly_type", anomaly.anomaly_type)\
              .eq("entity_type", anomaly.entity_type)\
              .eq("entity_id", anomaly.entity_id)\
              .eq("resolved", False)\
              .execute()

            if update_response.data:
                updated += 1
            else:
                # Nao existia, inserir
                insert_data = anomaly.to_insert_dict(run_id)
                insert_data["first_seen_at"] = datetime.now(timezone.utc).isoformat()
                insert_data["last_seen_at"] = datetime.now(timezone.utc).isoformat()
                insert_data["occurrence_count"] = 1

                supabase.table("data_anomalies").insert(insert_data).execute()
                inserted += 1

        except Exception as e:
            logger.error(f"Erro ao persistir anomalia {anomaly.entity_id}: {e}")

    return {"inserted": inserted, "updated": updated}


async def notify_anomalies_slack(
    anomalies: List[DataAnomaly],
    persist_result: dict
) -> bool:
    """Notifica anomalias no Slack com sumario."""
    if not anomalies:
        return True

    # Agrupar por direcao e tipo
    by_direction = {"db_to_events": {}, "events_to_db": {}}
    for a in anomalies:
        direction = a.direction
        if a.anomaly_type not in by_direction[direction]:
            by_direction[direction][a.anomaly_type] = 0
        by_direction[direction][a.anomaly_type] += 1

    # Severidade geral
    has_critical = any(a.severity == "critical" for a in anomalies)
    color = "#FF0000" if has_critical else "#FFA500"
    emoji = "🚨" if has_critical else "⚠️"

    # Formatar campos
    fields = []

    # DB → Eventos
    if by_direction["db_to_events"]:
        db_items = [f"{k}: {v}" for k, v in by_direction["db_to_events"].items()]
        fields.append({
            "title": "DB → Eventos",
            "value": "\n".join(db_items),
            "short": True
        })

    # Eventos → DB
    if by_direction["events_to_db"]:
        ev_items = [f"{k}: {v}" for k, v in by_direction["events_to_db"].items()]
        fields.append({
            "title": "Eventos → DB",
            "value": "\n".join(ev_items),
            "short": True
        })

    # Persistencia
    fields.append({
        "title": "Persistencia",
        "value": f"Novas: {persist_result['inserted']}, Recorrentes: {persist_result['updated']}",
        "short": True
    })

    message = {
        "text": f"{emoji} Reconciliacao: {len(anomalies)} divergencia(s)",
        "attachments": [
            {
                "color": color,
                "title": "Resultado da Reconciliacao Bidirecional",
                "fields": fields,
                "footer": "Sprint 18 - Data Integrity",
                "ts": int(datetime.now().timestamp()),
            }
        ],
    }

    return await enviar_slack(message)


async def reconciliation_job() -> dict:
    """
    Job diario de reconciliacao bidirecional.

    Executa:
    1. Reconciliacao DB → Eventos
    2. Reconciliacao Eventos → DB
    3. Persiste com deduplicacao
    4. Notifica Slack
    """
    run_id = str(uuid4())
    logger.info(f"Iniciando reconciliacao bidirecional (run_id={run_id})...")

    try:
        # Executar reconciliacao
        anomalies = await run_reconciliation(hours=24)

        if anomalies:
            logger.warning(f"Detectadas {len(anomalies)} divergencias")

            # Persistir com deduplicacao
            persist_result = await persist_anomalies_with_dedup(anomalies, run_id)
            logger.info(
                f"Persistencia: {persist_result['inserted']} novas, "
                f"{persist_result['updated']} atualizadas"
            )

            # Notificar
            await notify_anomalies_slack(anomalies, persist_result)

            # Agrupar por direcao para retorno
            by_dir = {
                "db_to_events": sum(1 for a in anomalies if a.direction == "db_to_events"),
                "events_to_db": sum(1 for a in anomalies if a.direction == "events_to_db"),
            }

            return {
                "status": "warning",
                "run_id": run_id,
                "total_anomalies": len(anomalies),
                "by_direction": by_dir,
                "persist_result": persist_result,
            }
        else:
            logger.info("Nenhuma divergencia detectada")
            return {
                "status": "ok",
                "run_id": run_id,
                "total_anomalies": 0,
            }

    except Exception as e:
        logger.error(f"Erro no job de reconciliacao: {e}")
        return {
            "status": "error",
            "run_id": run_id,
            "error": str(e),
        }
```

### DoD

- [ ] Servico implementado com reconciliacao bidirecional
- [ ] Deduplicacao funcionando (increment count)
- [ ] Notificacao Slack com sumario por direcao

---

## Story 11.4: Endpoints de Consulta

```python
# app/api/routes/metricas.py (adicao)

@router.get("/anomalias")
async def listar_anomalias(
    days: int = Query(7, ge=1, le=30, description="Ultimos N dias"),
    resolved: Optional[bool] = Query(None, description="Filtrar por status"),
    anomaly_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    entity_type: Optional[str] = Query(None, description="Filtrar por entidade"),
    severity: Optional[str] = Query(None, description="Filtrar por severidade"),
):
    """
    Lista anomalias de dados detectadas.

    Retorna anomalias com expected/found e count de recorrencia.
    """
    try:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()

        query = (
            supabase.table("data_anomalies")
            .select("*")
            .gte("last_seen_at", since)
            .order("last_seen_at", desc=True)
        )

        if resolved is not None:
            query = query.eq("resolved", resolved)
        if anomaly_type:
            query = query.eq("anomaly_type", anomaly_type)
        if entity_type:
            query = query.eq("entity_type", entity_type)
        if severity:
            query = query.eq("severity", severity)

        response = query.limit(100).execute()

        # Calcular sumario
        data = response.data or []
        summary = {
            "total": len(data),
            "by_type": {},
            "by_entity": {},
            "by_severity": {"warning": 0, "critical": 0},
            "recurring": sum(1 for a in data if a.get("occurrence_count", 1) > 1),
        }
        for a in data:
            t = a.get("anomaly_type", "unknown")
            summary["by_type"][t] = summary["by_type"].get(t, 0) + 1
            e = a.get("entity_type", "unknown")
            summary["by_entity"][e] = summary["by_entity"].get(e, 0) + 1
            s = a.get("severity", "warning")
            summary["by_severity"][s] = summary["by_severity"].get(s, 0) + 1

        return {
            "period_days": days,
            "summary": summary,
            "anomalies": data,
        }

    except Exception as e:
        logger.error(f"Erro ao listar anomalias: {e}")
        return {"period_days": days, "summary": {}, "anomalies": [], "error": str(e)}


@router.get("/anomalias/recorrentes")
async def listar_anomalias_recorrentes(
    min_count: int = Query(3, ge=2, description="Minimo de ocorrencias"),
):
    """
    Lista anomalias recorrentes (detectadas multiplas vezes).

    Util para identificar problemas sistematicos.
    """
    try:
        response = (
            supabase.table("data_anomalies")
            .select("*")
            .eq("resolved", False)
            .gte("occurrence_count", min_count)
            .order("occurrence_count", desc=True)
            .limit(50)
            .execute()
        )

        return {
            "min_count": min_count,
            "total": len(response.data or []),
            "anomalies": response.data or [],
        }

    except Exception as e:
        logger.error(f"Erro ao listar recorrentes: {e}")
        return {"min_count": min_count, "total": 0, "anomalies": [], "error": str(e)}


@router.post("/anomalias/{anomaly_id}/resolver")
async def resolver_anomalia(
    anomaly_id: str,
    resolution_notes: str = Query(..., description="Notas de resolucao"),
    resolved_by: str = Query("sistema", description="Quem resolveu"),
):
    """Marca anomalia como resolvida."""
    try:
        supabase.table("data_anomalies").update({
            "resolved": True,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
            "resolved_by": resolved_by,
            "resolution_notes": resolution_notes,
        }).eq("id", anomaly_id).execute()

        return {"status": "ok", "message": "Anomalia resolvida"}

    except Exception as e:
        logger.error(f"Erro ao resolver anomalia: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
```

### DoD

- [ ] Endpoint GET `/metricas/anomalias` com sumario
- [ ] Endpoint GET `/metricas/anomalias/recorrentes`
- [ ] Endpoint POST `/metricas/anomalias/{id}/resolver`
- [ ] Filtros por tipo, entidade, severidade

---

## Checklist do Epico

- [ ] **S18.E11.1** - Tabela data_anomalies com schema melhorado
- [ ] **S18.E11.2** - Reconciliacao bidirecional (DB→Eventos + Eventos→DB)
- [ ] **S18.E11.3** - Servico com deduplicacao e tracking de recorrencia
- [ ] **S18.E11.4** - Endpoints de consulta com sumarios
- [ ] Ambas direcoes cobertas
- [ ] Anomalias recorrentes identificaveis
- [ ] Alertas Slack com breakdown por direcao
