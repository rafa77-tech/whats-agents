# Sistema de Incidentes de Saúde

**Sprint:** 55 - Epic 03
**Módulo:** Health Monitoring
**Tabela:** `health_incidents`

## Visão Geral

O sistema de incidentes registra e rastreia mudanças no status de saúde do sistema, permitindo análise de uptime, MTTR (Mean Time To Recover), e histórico de degradações. Integra-se com health checks do dashboard para detectar automaticamente transições críticas.

## O Que São Incidentes

Incidentes são registros de mudanças de status do sistema que indicam degradação ou recuperação. Cada incidente captura:

- **Status inicial e final** (ex: `healthy` → `critical`)
- **Score de saúde** (0-100)
- **Origem do trigger** (dashboard, health check, manual)
- **Detalhes técnicos** (componentes afetados, métricas)
- **Duração** (calculada automaticamente quando resolvido)

### Estados de Sistema

| Status | Score | Descrição |
|--------|-------|-----------|
| `healthy` | 90-100 | Sistema operando normalmente |
| `degraded` | 60-89 | Desempenho reduzido, mas funcional |
| `critical` | 0-59 | Sistema com falhas graves |

## API Endpoints

### POST /incidents

Registra uma mudança de status do sistema.

**Request Body:**

```json
{
  "from_status": "healthy",
  "to_status": "critical",
  "from_score": 95,
  "to_score": 45,
  "trigger_source": "dashboard",
  "details": {
    "componentes_afetados": ["chips", "fila"],
    "motivo": "Rate limit excedido em múltiplos chips"
  }
}
```

**Campos:**

- `from_status` (opcional): Status anterior
- `to_status` (obrigatório): Status atual
- `from_score` (opcional): Score anterior
- `to_score` (obrigatório): Score atual
- `trigger_source` (default: "api"): Origem do evento
- `details` (opcional): Objeto JSON com detalhes

**Response:**

```json
{
  "success": true,
  "incident_id": "uuid-do-incidente"
}
```

**Comportamento Especial:**

Quando o status muda de `critical` para qualquer outro, o endpoint automaticamente resolve o incidente crítico ativo anterior (se houver), calculando a duração.

### GET /incidents

Lista histórico de incidentes.

**Query Parameters:**

- `limit` (default: 20): Número máximo de resultados
- `status` (opcional): Filtrar por status final (`healthy`, `degraded`, `critical`)
- `since` (opcional): Data ISO 8601 (ex: `2026-02-01T00:00:00Z`)

**Response:**

```json
{
  "incidents": [
    {
      "id": "uuid",
      "from_status": "healthy",
      "to_status": "critical",
      "from_score": 95,
      "to_score": 45,
      "trigger_source": "dashboard",
      "details": {},
      "started_at": "2026-02-10T10:30:00Z",
      "resolved_at": "2026-02-10T10:45:00Z",
      "duration_seconds": 900
    }
  ],
  "total": 1
}
```

### GET /incidents/stats

Retorna estatísticas agregadas de incidentes.

**Query Parameters:**

- `dias` (default: 30): Período de análise

**Response:**

```json
{
  "period_days": 30,
  "total_incidents": 15,
  "critical_incidents": 3,
  "degraded_incidents": 8,
  "mttr_seconds": 1200,
  "uptime_percent": 99.85
}
```

**Métricas:**

- `total_incidents`: Total de mudanças de status
- `critical_incidents`: Quantos entraram em estado crítico
- `degraded_incidents`: Quantos entraram em estado degradado
- `mttr_seconds`: Tempo médio de recuperação (média de `duration_seconds`)
- `uptime_percent`: Percentual do tempo fora de estado crítico

## Como Usar

### 1. Criar Incidente (Dashboard)

O dashboard detecta automaticamente mudanças de status via health checks:

```typescript
// dashboard/app/components/HealthMonitor.tsx
const handleStatusChange = async (newStatus, newScore) => {
  await fetch('/api/incidents', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from_status: currentStatus,
      to_status: newStatus,
      from_score: currentScore,
      to_score: newScore,
      trigger_source: 'dashboard',
      details: {
        timestamp: new Date().toISOString(),
        health_checks: healthCheckResults
      }
    })
  });
};
```

### 2. Visualizar Incidentes

No dashboard:

1. Navegar para **Monitoramento > Health**
2. Seção "Histórico de Incidentes" exibe últimos 20
3. Filtrar por status ou período

Via API:

```bash
# Últimos 10 incidentes críticos
curl "https://api.revoluna.com/incidents?status=critical&limit=10"

# Incidentes da última semana
curl "https://api.revoluna.com/incidents?since=2026-02-03T00:00:00Z"
```

### 3. Resolver Incidente

Incidentes são resolvidos automaticamente quando o sistema sai do estado crítico. Não há endpoint manual de resolução.

**Fluxo:**

1. Sistema entra em `critical` → Incidente criado (`resolved_at = null`)
2. Sistema volta para `healthy` ou `degraded` → Função interna `_resolver_incidente_ativo()` é chamada
3. Incidente atualizado com `resolved_at` e `duration_seconds`

### 4. Analisar Estatísticas

```bash
# Estatísticas dos últimos 7 dias
curl "https://api.revoluna.com/incidents/stats?dias=7"

# Últimos 30 dias (default)
curl "https://api.revoluna.com/incidents/stats"
```

## Integração com Health Checks

O sistema de incidentes funciona em conjunto com health checks periódicos:

1. **Health Check** roda a cada 5 minutos (configur��vel)
2. Calcula score de saúde (0-100) baseado em:
   - Status dos chips WhatsApp
   - Fila de mensagens (pendentes/falhadas)
   - Rate limits ativos
   - Handoffs não resolvidos
3. Determina status: `healthy`, `degraded`, ou `critical`
4. Se status mudou, cria incidente via `POST /incidents`

### Tabela health_incidents

```sql
CREATE TABLE health_incidents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_status TEXT,
    to_status TEXT NOT NULL,
    from_score INTEGER,
    to_score INTEGER NOT NULL,
    trigger_source TEXT DEFAULT 'api',
    details JSONB DEFAULT '{}'::jsonb,
    started_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_health_incidents_status ON health_incidents(to_status);
CREATE INDEX idx_health_incidents_started ON health_incidents(started_at DESC);
```

## Troubleshooting

### Problema: Incidentes não são criados automaticamente

**Diagnóstico:**

1. Verificar se health checks estão rodando:
   ```bash
   railway logs | grep "health_check"
   ```

2. Verificar erros no endpoint:
   ```bash
   railway logs | grep "POST /incidents"
   ```

**Solução:**

- Health checks podem estar desabilitados no dashboard
- Verificar configuração de intervalo em `dashboard/app/config/health.ts`

### Problema: Incidentes não são resolvidos

**Diagnóstico:**

1. Verificar se sistema voltou para status não-crítico:
   ```sql
   SELECT * FROM health_incidents
   WHERE to_status = 'critical'
   AND resolved_at IS NULL
   ORDER BY started_at DESC;
   ```

2. Checar logs da função de resolução:
   ```bash
   railway logs | grep "_resolver_incidente_ativo"
   ```

**Solução:**

- Se incidente permanece ativo mas sistema está `healthy`, foi um erro na transição
- Resolver manualmente via SQL:
  ```sql
  UPDATE health_incidents
  SET resolved_at = NOW(),
      duration_seconds = EXTRACT(EPOCH FROM (NOW() - started_at))
  WHERE id = 'uuid-do-incidente';
  ```

### Problema: MTTR muito alto

**Causas comuns:**

1. Chips ficando offline por períodos longos (problema de rede)
2. Rate limits não sendo respeitados (loops de retry)
3. Fila de mensagens acumulando (processamento lento)

**Ação:**

1. Analisar detalhes dos incidentes longos:
   ```sql
   SELECT
     id,
     details,
     duration_seconds / 60 as duration_minutes
   FROM health_incidents
   WHERE to_status = 'critical'
   AND duration_seconds > 600  -- Mais de 10 minutos
   ORDER BY duration_seconds DESC
   LIMIT 10;
   ```

2. Investigar componentes afetados no campo `details`
3. Ajustar thresholds de health check se necessário

## Métricas de Sucesso

| Métrica | Meta | Como Medir |
|---------|------|------------|
| Uptime | > 99.5% | `GET /incidents/stats` → `uptime_percent` |
| MTTR | < 5 min | `GET /incidents/stats` → `mttr_seconds` |
| Incidentes críticos/mês | < 5 | `GET /incidents?status=critical&since=[mês]` |

## Próximos Passos

1. **Alertas**: Integrar com Slack para notificações de incidentes críticos
2. **Postmortem**: Template automático para incidentes com duração > 30 min
3. **Prevenção**: Detectar padrões recorrentes e sugerir ações proativas
4. **SLA Tracking**: Dashboard com histórico de uptime por dia/semana/mês
