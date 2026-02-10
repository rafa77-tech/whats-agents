# ÉPICO 03: Histórico de Incidentes

## Contexto

Atualmente, quando o sistema fica degradado ou crítico, não há registro histórico. Isso dificulta:
- Análise pós-incidente
- Identificação de padrões (horários problemáticos)
- Métricas de disponibilidade (uptime)

Este épico adiciona uma tabela para registrar mudanças de status e uma timeline visual no dashboard.

## Escopo

- **Incluído**:
  - Tabela `health_incidents` no Supabase
  - Registro automático de mudanças de status
  - Timeline de incidentes no Health Center
  - Métricas básicas de uptime

- **Excluído**:
  - Alertas por email
  - Relatórios automáticos
  - Integração com ferramentas externas (PagerDuty, etc)

---

## Tarefa T03.1: Tabela de Incidentes

### Objetivo

Criar tabela para armazenar histórico de mudanças de status.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | Migration via MCP Supabase |

### Implementação

```sql
-- Migration: create_health_incidents_table
-- Descrição: Tabela para histórico de incidentes de saúde do sistema

CREATE TABLE IF NOT EXISTS health_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Status
    from_status VARCHAR(20),  -- null = primeiro registro
    to_status VARCHAR(20) NOT NULL,

    -- Score
    from_score INTEGER,
    to_score INTEGER NOT NULL,

    -- Detalhes
    trigger_source VARCHAR(50) NOT NULL,  -- 'dashboard', 'api', 'job'
    details JSONB DEFAULT '{}',  -- alertas ativos, serviços down, etc

    -- Timestamps
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,  -- null se ainda ativo
    duration_seconds INTEGER,  -- calculado no resolve

    -- Metadata
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índices
CREATE INDEX idx_health_incidents_started_at ON health_incidents(started_at DESC);
CREATE INDEX idx_health_incidents_to_status ON health_incidents(to_status);
CREATE INDEX idx_health_incidents_active ON health_incidents(resolved_at) WHERE resolved_at IS NULL;

-- RLS
ALTER TABLE health_incidents ENABLE ROW LEVEL SECURITY;

-- Policy: apenas service role pode inserir/atualizar
CREATE POLICY "Service role full access" ON health_incidents
    FOR ALL USING (true) WITH CHECK (true);

-- Comentários
COMMENT ON TABLE health_incidents IS 'Histórico de mudanças de status de saúde do sistema';
COMMENT ON COLUMN health_incidents.from_status IS 'Status anterior (null no primeiro registro)';
COMMENT ON COLUMN health_incidents.to_status IS 'Novo status (healthy, degraded, critical)';
COMMENT ON COLUMN health_incidents.trigger_source IS 'Origem da detecção (dashboard, api, job)';
```

### Testes Obrigatórios

**Verificação:**
- [ ] Tabela criada com todas as colunas
- [ ] Índices existem
- [ ] RLS habilitado

### Definition of Done

- [ ] Migration aplicada
- [ ] Tabela existe no banco
- [ ] Documentada no schema

### Estimativa

30 minutos

---

## Tarefa T03.2: Endpoint de Registro de Incidentes

### Objetivo

Criar endpoint para registrar e consultar incidentes.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `app/api/routes/incidents.py` |

### Implementação

```python
"""
Rotas de incidentes de saúde.

Sprint 55 - Epic 03
"""
from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from app.core.timezone import agora_utc
from app.services.supabase import supabase

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/incidents")
async def registrar_incidente(
    from_status: Optional[str],
    to_status: str,
    from_score: Optional[int],
    to_score: int,
    trigger_source: str = "api",
    details: dict = None,
):
    """
    Registra uma mudança de status.

    Chamado pelo dashboard quando detecta transição.
    """
    try:
        # Se mudando para não-crítico, resolver incidente anterior
        if to_status != "critical" and from_status == "critical":
            await _resolver_incidente_ativo()

        # Inserir novo incidente
        result = supabase.table("health_incidents").insert({
            "from_status": from_status,
            "to_status": to_status,
            "from_score": from_score,
            "to_score": to_score,
            "trigger_source": trigger_source,
            "details": details or {},
            "started_at": agora_utc().isoformat(),
        }).execute()

        return {"success": True, "incident_id": result.data[0]["id"]}

    except Exception as e:
        logger.error(f"Erro ao registrar incidente: {e}")
        return {"success": False, "error": str(e)}


@router.get("/incidents")
async def listar_incidentes(
    limit: int = 20,
    status: Optional[str] = None,
    since: Optional[str] = None,
):
    """
    Lista histórico de incidentes.
    """
    try:
        query = supabase.table("health_incidents").select("*")

        if status:
            query = query.eq("to_status", status)

        if since:
            query = query.gte("started_at", since)

        result = query.order("started_at", desc=True).limit(limit).execute()

        return {
            "incidents": result.data,
            "total": len(result.data),
        }

    except Exception as e:
        logger.error(f"Erro ao listar incidentes: {e}")
        return {"incidents": [], "error": str(e)}


@router.get("/incidents/stats")
async def estatisticas_incidentes(dias: int = 30):
    """
    Retorna estatísticas de incidentes.
    """
    try:
        since = (agora_utc() - timedelta(days=dias)).isoformat()

        result = supabase.table("health_incidents").select(
            "to_status, duration_seconds"
        ).gte("started_at", since).execute()

        incidents = result.data or []

        # Calcular métricas
        total = len(incidents)
        critical_count = len([i for i in incidents if i["to_status"] == "critical"])
        degraded_count = len([i for i in incidents if i["to_status"] == "degraded"])

        # MTTR (Mean Time To Recover)
        resolved = [i for i in incidents if i.get("duration_seconds")]
        mttr = sum(i["duration_seconds"] for i in resolved) / len(resolved) if resolved else 0

        # Uptime aproximado (período total - tempo em crítico)
        total_seconds = dias * 24 * 60 * 60
        critical_time = sum(i.get("duration_seconds", 0) for i in incidents if i["to_status"] == "critical")
        uptime_pct = ((total_seconds - critical_time) / total_seconds) * 100

        return {
            "period_days": dias,
            "total_incidents": total,
            "critical_incidents": critical_count,
            "degraded_incidents": degraded_count,
            "mttr_seconds": int(mttr),
            "uptime_percent": round(uptime_pct, 2),
        }

    except Exception as e:
        logger.error(f"Erro ao calcular estatísticas: {e}")
        return {"error": str(e)}


async def _resolver_incidente_ativo():
    """Resolve o incidente crítico ativo (se houver)."""
    try:
        # Buscar incidente ativo
        result = supabase.table("health_incidents").select("id, started_at").eq(
            "to_status", "critical"
        ).is_("resolved_at", "null").order("started_at", desc=True).limit(1).execute()

        if not result.data:
            return

        incident = result.data[0]
        started = datetime.fromisoformat(incident["started_at"].replace("Z", "+00:00"))
        duration = int((agora_utc() - started).total_seconds())

        # Atualizar como resolvido
        supabase.table("health_incidents").update({
            "resolved_at": agora_utc().isoformat(),
            "duration_seconds": duration,
        }).eq("id", incident["id"]).execute()

        logger.info(f"Incidente {incident['id']} resolvido após {duration}s")

    except Exception as e:
        logger.error(f"Erro ao resolver incidente: {e}")
```

### Testes Obrigatórios

**Unitários:**
- [ ] `registrar_incidente` insere corretamente
- [ ] `listar_incidentes` filtra por status
- [ ] `estatisticas_incidentes` calcula MTTR corretamente
- [ ] `_resolver_incidente_ativo` atualiza duração

**Arquivo:** `tests/api/test_incidents.py`

### Definition of Done

- [ ] Endpoints implementados
- [ ] Testes unitários passando
- [ ] Registrado no router principal

### Estimativa

1.5 horas

---

## Tarefa T03.3: Timeline de Incidentes no Dashboard

### Objetivo

Adicionar componente visual de timeline no Health Center.

### Arquivos

| Ação | Arquivo |
|------|---------|
| Criar | `dashboard/components/health/incidents-timeline.tsx` |
| Modificar | `dashboard/components/health/health-page-content.tsx` |

### Implementação

```typescript
// dashboard/components/health/incidents-timeline.tsx
'use client'

import { useState, useEffect } from 'react'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { AlertTriangle, CheckCircle2, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDistanceToNow } from 'date-fns'
import { ptBR } from 'date-fns/locale'

interface Incident {
  id: string
  from_status: string | null
  to_status: string
  from_score: number | null
  to_score: number
  started_at: string
  resolved_at: string | null
  duration_seconds: number | null
}

interface IncidentsTimelineProps {
  className?: string
}

export function IncidentsTimeline({ className }: IncidentsTimelineProps) {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [stats, setStats] = useState<{
    total_incidents: number
    critical_incidents: number
    mttr_seconds: number
    uptime_percent: number
  } | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchData() {
      try {
        const [incidentsRes, statsRes] = await Promise.all([
          fetch('/api/incidents?limit=10'),
          fetch('/api/incidents/stats?dias=7'),
        ])

        if (incidentsRes.ok) {
          const data = await incidentsRes.json()
          setIncidents(data.incidents || [])
        }

        if (statsRes.ok) {
          setStats(await statsRes.json())
        }
      } catch (e) {
        console.error('Error fetching incidents:', e)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex h-48 items-center justify-center">
          <div className="animate-pulse text-muted-foreground">Carregando...</div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Histórico de Incidentes</CardTitle>
          {stats && (
            <Badge variant="outline" className="font-mono">
              Uptime 7d: {stats.uptime_percent}%
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {/* Stats resumo */}
        {stats && (
          <div className="mb-4 grid grid-cols-3 gap-4 text-center text-sm">
            <div>
              <div className="text-2xl font-bold">{stats.total_incidents}</div>
              <div className="text-muted-foreground">Incidentes (7d)</div>
            </div>
            <div>
              <div className="text-2xl font-bold text-status-error-foreground">
                {stats.critical_incidents}
              </div>
              <div className="text-muted-foreground">Críticos</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {stats.mttr_seconds > 0
                  ? `${Math.round(stats.mttr_seconds / 60)}min`
                  : '-'}
              </div>
              <div className="text-muted-foreground">MTTR</div>
            </div>
          </div>
        )}

        {/* Timeline */}
        <div className="space-y-3">
          {incidents.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <CheckCircle2 className="mx-auto h-8 w-8 text-status-success-foreground" />
              <p className="mt-2">Nenhum incidente registrado</p>
            </div>
          ) : (
            incidents.map((incident) => (
              <div
                key={incident.id}
                className={cn(
                  'flex items-start gap-3 rounded-lg border p-3',
                  incident.to_status === 'critical' && 'border-status-error-border bg-status-error/10',
                  incident.to_status === 'degraded' && 'border-status-warning-border bg-status-warning/10',
                  incident.to_status === 'healthy' && 'border-status-success-border bg-status-success/10'
                )}
              >
                <div className="mt-0.5">
                  {incident.to_status === 'critical' && (
                    <AlertTriangle className="h-5 w-5 text-status-error-foreground" />
                  )}
                  {incident.to_status === 'degraded' && (
                    <AlertTriangle className="h-5 w-5 text-status-warning-foreground" />
                  )}
                  {incident.to_status === 'healthy' && (
                    <CheckCircle2 className="h-5 w-5 text-status-success-foreground" />
                  )}
                </div>
                <div className="flex-1">
                  <div className="flex items-center justify-between">
                    <span className="font-medium capitalize">{incident.to_status}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatDistanceToNow(new Date(incident.started_at), {
                        addSuffix: true,
                        locale: ptBR,
                      })}
                    </span>
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                    <span>Score: {incident.to_score}</span>
                    {incident.duration_seconds && (
                      <>
                        <span>•</span>
                        <Clock className="h-3 w-3" />
                        <span>{Math.round(incident.duration_seconds / 60)}min</span>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  )
}
```

### Testes Obrigatórios

**Unitários:**
- [ ] Renderiza loading state
- [ ] Renderiza empty state
- [ ] Renderiza lista de incidentes corretamente
- [ ] Formata datas em português

**E2E:**
- [ ] Timeline aparece na página /health
- [ ] Stats mostram valores corretos

### Definition of Done

- [ ] Componente implementado
- [ ] Integrado no Health Center
- [ ] Testes passando

### Estimativa

1 hora

---

## Resumo do Épico

| Tarefa | Estimativa | Risco |
|--------|------------|-------|
| T03.1: Tabela de incidentes | 30min | Baixo |
| T03.2: Endpoint de incidentes | 1.5h | Baixo |
| T03.3: Timeline no dashboard | 1h | Baixo |
| **Total** | **3h** | |

## Ordem de Execução

1. T03.1 - Criar tabela (backend depende dela)
2. T03.2 - Endpoints de API
3. T03.3 - Componente frontend

## Paralelizável

- Nenhuma tarefa paralelizável (dependência sequencial)
