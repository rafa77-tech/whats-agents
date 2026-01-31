# Epic 02: Types Monitor

## Objetivo

Criar os tipos TypeScript para a página Monitor, seguindo o padrão de `types/dashboard.ts` e `types/chips.ts`.

## Contexto

Antes de implementar componentes e APIs, precisamos definir os tipos para garantir type safety e documentação clara das estruturas de dados.

---

## Story 2.1: Criar Arquivo types/monitor.ts

### Objetivo
Criar o arquivo de tipos com todas as interfaces necessárias.

### Tarefas

1. **Criar arquivo de tipos:**

**Arquivo:** `dashboard/types/monitor.ts`

```typescript
/**
 * Monitor Types - Sprint 42
 *
 * Tipos para a página de monitoramento de jobs e saúde do sistema.
 */

// ============================================================================
// Job Status Types
// ============================================================================

/**
 * Status de execução de um job.
 * - running: Job está executando
 * - success: Job completou com sucesso
 * - error: Job falhou com erro
 * - timeout: Job excedeu timeout (300s)
 */
export type JobStatus = 'running' | 'success' | 'error' | 'timeout'

/**
 * Categoria de job baseada na frequência de execução.
 * Usado para agrupamento visual e cálculo de SLA.
 */
export type JobCategory = 'critical' | 'frequent' | 'hourly' | 'daily' | 'weekly'

/**
 * Definição estática de um job do sistema.
 * Baseado na lista JOBS de app/workers/scheduler.py.
 */
export interface JobDefinition {
  /** Nome único do job (ex: "heartbeat", "processar_mensagens_agendadas") */
  name: string
  /** Categoria do job para agrupamento */
  category: JobCategory
  /** Expressão cron do schedule (ex: "* * * * *") */
  schedule: string
  /** Descrição legível do job */
  description: string
  /** SLA em segundos (tempo máximo entre execuções) */
  slaSeconds: number
  /** Se é um job crítico (deve estar sempre rodando) */
  isCritical: boolean
}

/**
 * Registro de uma execução de job.
 * Mapeado da tabela job_executions do Supabase.
 */
export interface JobExecution {
  /** UUID da execução */
  id: string
  /** Nome do job */
  jobName: string
  /** Timestamp de início (ISO 8601) */
  startedAt: string
  /** Timestamp de fim (ISO 8601), null se ainda executando */
  finishedAt: string | null
  /** Status da execução */
  status: JobStatus
  /** Duração em milissegundos, null se ainda executando */
  durationMs: number | null
  /** Código HTTP da resposta, null se não aplicável */
  responseCode: number | null
  /** Mensagem de erro (truncada em 500 chars), null se sucesso */
  error: string | null
  /** Número de itens processados, null se não reportado */
  itemsProcessed: number | null
}

/**
 * Resumo agregado de um job para exibição na tabela.
 * Calculado a partir de múltiplas execuções.
 */
export interface JobSummary {
  /** Nome do job */
  name: string
  /** Categoria do job */
  category: JobCategory
  /** Expressão cron */
  schedule: string
  /** Descrição do job */
  description: string
  /** Timestamp da última execução */
  lastRun: string | null
  /** Status da última execução */
  lastStatus: JobStatus | null
  /** Timestamp esperado da próxima execução */
  nextExpectedRun: string | null
  /** Total de execuções nas últimas 24h */
  runs24h: number
  /** Execuções com sucesso nas últimas 24h */
  success24h: number
  /** Execuções com erro nas últimas 24h */
  errors24h: number
  /** Execuções com timeout nas últimas 24h */
  timeouts24h: number
  /** Duração média em ms */
  avgDurationMs: number
  /** Total de itens processados nas últimas 24h */
  totalItemsProcessed: number
  /** Último erro (se houver) */
  lastError: string | null
  /** SLA em segundos */
  slaSeconds: number
  /** Se está atrasado (excedeu SLA) */
  isStale: boolean
  /** Segundos desde última execução */
  secondsSinceLastRun: number | null
  /** Se é um job crítico */
  isCritical: boolean
}

// ============================================================================
// System Health Types
// ============================================================================

/**
 * Status geral de saúde do sistema.
 */
export type SystemHealthStatus = 'healthy' | 'degraded' | 'critical'

/**
 * Dados de saúde do sistema.
 */
export interface SystemHealthData {
  /** Status geral */
  status: SystemHealthStatus
  /** Score de 0-100 */
  score: number
  /** Breakdown por subsistema */
  checks: {
    /** Jobs (sucesso vs falhas) */
    jobs: { score: number; max: number; details: string }
    /** Conectividade (WhatsApp, Redis, Supabase) */
    connectivity: { score: number; max: number; details: string }
    /** Fila de mensagens */
    fila: { score: number; max: number; details: string }
    /** Pool de chips */
    chips: { score: number; max: number; details: string }
  }
  /** Última atualização */
  lastUpdated: string
}

// ============================================================================
// API Response Types
// ============================================================================

/**
 * Resposta de GET /api/dashboard/monitor
 * Overview geral do sistema.
 */
export interface MonitorOverviewResponse {
  /** Dados de saúde do sistema */
  systemHealth: SystemHealthData
  /** Estatísticas agregadas dos jobs */
  jobsStats: {
    /** Total de jobs configurados */
    totalJobs: number
    /** Taxa de sucesso nas últimas 24h (0-100) */
    successRate24h: number
    /** Número de jobs que falharam nas últimas 24h */
    failedJobs24h: number
    /** Número de jobs executando agora */
    runningJobs: number
    /** Número de jobs atrasados (stale) */
    staleJobs: number
  }
  /** Alertas ativos */
  alerts: {
    /** Jobs críticos atrasados */
    criticalStale: string[]
    /** Jobs com erros nas últimas 24h */
    jobsWithErrors: string[]
    /** Jobs com timeouts nas últimas 24h */
    jobsWithTimeouts: string[]
    /** Jobs críticos que nunca executaram */
    missingCritical: string[]
  }
  /** Timestamp da resposta */
  timestamp: string
}

/**
 * Resposta de GET /api/dashboard/monitor/jobs
 * Lista de jobs com resumo.
 */
export interface MonitorJobsResponse {
  /** Lista de jobs com resumo */
  jobs: JobSummary[]
  /** Total de jobs */
  total: number
  /** Período consultado */
  period: string
  /** Timestamp da resposta */
  timestamp: string
}

/**
 * Resposta de GET /api/dashboard/monitor/job/[name]/executions
 * Histórico de execuções de um job específico.
 */
export interface JobExecutionsResponse {
  /** Nome do job */
  jobName: string
  /** Lista de execuções */
  executions: JobExecution[]
  /** Total de execuções (para paginação) */
  total: number
  /** Página atual */
  page: number
  /** Tamanho da página */
  pageSize: number
  /** Se há mais páginas */
  hasMore: boolean
}

// ============================================================================
// Filter Types
// ============================================================================

/**
 * Filtro de status para a lista de jobs.
 */
export type JobStatusFilter = 'all' | JobStatus | 'stale'

/**
 * Filtro de período de tempo.
 */
export type TimeRangeFilter = '1h' | '6h' | '24h'

/**
 * Estado dos filtros na página.
 */
export interface MonitorFilters {
  /** Filtro de status */
  status: JobStatusFilter
  /** Filtro de período */
  timeRange: TimeRangeFilter
  /** Filtro de busca por nome */
  search: string
  /** Filtro de categoria */
  category: JobCategory | 'all'
}

// ============================================================================
// UI State Types
// ============================================================================

/**
 * Estado de ordenação da tabela.
 */
export interface JobsTableSort {
  /** Coluna de ordenação */
  column: 'name' | 'lastRun' | 'status' | 'duration' | 'successRate'
  /** Direção */
  direction: 'asc' | 'desc'
}

/**
 * Props do modal de detalhes do job.
 */
export interface JobDetailModalProps {
  /** Se o modal está aberto */
  open: boolean
  /** Callback para fechar */
  onOpenChange: (open: boolean) => void
  /** Nome do job selecionado */
  jobName: string | null
}
```

### DoD

- [ ] Arquivo `types/monitor.ts` criado
- [ ] Todos os tipos documentados com JSDoc
- [ ] Tipos cobrem todos os casos de uso:
  - [ ] JobStatus, JobCategory
  - [ ] JobExecution, JobSummary, JobDefinition
  - [ ] SystemHealthData, SystemHealthStatus
  - [ ] MonitorOverviewResponse, MonitorJobsResponse, JobExecutionsResponse
  - [ ] MonitorFilters, JobStatusFilter, TimeRangeFilter
  - [ ] JobsTableSort, JobDetailModalProps
- [ ] Sem uso de `any`
- [ ] Compatível com dados da tabela job_executions

---

## Story 2.2: Criar Constantes de Jobs

### Objetivo
Criar arquivo com definições estáticas dos 32 jobs do sistema.

### Tarefas

1. **Criar arquivo de constantes:**

**Arquivo:** `dashboard/lib/monitor/jobs-config.ts`

```typescript
/**
 * Jobs Configuration - Sprint 42
 *
 * Definições estáticas dos jobs do sistema.
 * Baseado em app/workers/scheduler.py.
 */

import type { JobDefinition, JobCategory } from '@/types/monitor'

/**
 * SLA por categoria de job (em segundos).
 */
export const JOB_SLA_BY_CATEGORY: Record<JobCategory, number> = {
  critical: 180,      // 3 minutos
  frequent: 900,      // 15 minutos
  hourly: 7200,       // 2 horas
  daily: 90000,       // 25 horas
  weekly: 691200,     // 8 dias
}

/**
 * Lista completa de jobs do sistema.
 */
export const JOBS: JobDefinition[] = [
  // Critical (every minute)
  {
    name: 'heartbeat',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Heartbeat para monitoramento',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_mensagens_agendadas',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Processa mensagens da fila',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_campanhas_agendadas',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Processa campanhas agendadas',
    slaSeconds: 180,
    isCritical: true,
  },
  {
    name: 'processar_grupos',
    category: 'critical',
    schedule: '* * * * *',
    description: 'Processa mensagens de grupos',
    slaSeconds: 180,
    isCritical: true,
  },

  // Frequent (every 5-15 min)
  {
    name: 'verificar_whatsapp',
    category: 'frequent',
    schedule: '*/5 * * * *',
    description: 'Verifica conexão WhatsApp',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'sincronizar_chips',
    category: 'frequent',
    schedule: '*/5 * * * *',
    description: 'Sincroniza chips com Evolution API',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'validar_telefones',
    category: 'frequent',
    schedule: '*/5 8-19 * * *',
    description: 'Valida telefones via checkNumberStatus',
    slaSeconds: 900,
    isCritical: false,
  },
  {
    name: 'atualizar_trust_scores',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Atualiza trust scores dos chips',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'verificar_alertas',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Verifica alertas do sistema',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'verificar_alertas_grupos',
    category: 'frequent',
    schedule: '*/15 * * * *',
    description: 'Verifica alertas de grupos',
    slaSeconds: 2700,
    isCritical: false,
  },
  {
    name: 'processar_handoffs',
    category: 'frequent',
    schedule: '*/10 * * * *',
    description: 'Processa follow-ups de handoff',
    slaSeconds: 1800,
    isCritical: false,
  },

  // Hourly
  {
    name: 'sincronizar_briefing',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Sincroniza briefing do Google Docs',
    slaSeconds: 7200,
    isCritical: false,
  },
  {
    name: 'processar_confirmacao_plantao',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Processa confirmações de plantão',
    slaSeconds: 7200,
    isCritical: false,
  },
  {
    name: 'oferta_autonoma',
    category: 'hourly',
    schedule: '0 * * * *',
    description: 'Executa ofertas autônomas',
    slaSeconds: 7200,
    isCritical: false,
  },

  // Daily
  {
    name: 'processar_followups',
    category: 'daily',
    schedule: '0 10 * * *',
    description: 'Processa follow-ups diários',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'processar_pausas_expiradas',
    category: 'daily',
    schedule: '0 6 * * *',
    description: 'Processa pausas expiradas',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'avaliar_conversas_pendentes',
    category: 'daily',
    schedule: '0 2 * * *',
    description: 'Avalia conversas pendentes',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'report_manha',
    category: 'daily',
    schedule: '0 10 * * *',
    description: 'Report da manhã',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'report_fim_dia',
    category: 'daily',
    schedule: '0 20 * * *',
    description: 'Report de fim do dia',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'doctor_state_manutencao_diaria',
    category: 'daily',
    schedule: '0 3 * * *',
    description: 'Manutenção diária do doctor_state',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'sincronizar_templates',
    category: 'daily',
    schedule: '0 6 * * *',
    description: 'Sincroniza templates de campanha',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'limpar_grupos_finalizados',
    category: 'daily',
    schedule: '0 3 * * *',
    description: 'Limpa grupos finalizados',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'consolidar_metricas_grupos',
    category: 'daily',
    schedule: '0 1 * * *',
    description: 'Consolida métricas de grupos',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'processar_retomadas',
    category: 'daily',
    schedule: '0 8 * * 1-5',
    description: 'Processa retomadas (seg-sex)',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'discovery_autonomo',
    category: 'daily',
    schedule: '0 9,14 * * 1-5',
    description: 'Discovery autônomo (9h e 14h)',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'feedback_autonomo',
    category: 'daily',
    schedule: '0 11 * * *',
    description: 'Feedback autônomo',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'snapshot_chips_diario',
    category: 'daily',
    schedule: '55 23 * * *',
    description: 'Snapshot diário de chips',
    slaSeconds: 90000,
    isCritical: false,
  },
  {
    name: 'resetar_contadores_chips',
    category: 'daily',
    schedule: '5 0 * * *',
    description: 'Reset de contadores de chips',
    slaSeconds: 90000,
    isCritical: false,
  },

  // Weekly
  {
    name: 'report_semanal',
    category: 'weekly',
    schedule: '0 9 * * 1',
    description: 'Report semanal (segunda)',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'atualizar_prompt_feedback',
    category: 'weekly',
    schedule: '0 2 * * 0',
    description: 'Atualiza prompt de feedback',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'doctor_state_manutencao_semanal',
    category: 'weekly',
    schedule: '0 4 * * 1',
    description: 'Manutenção semanal doctor_state',
    slaSeconds: 691200,
    isCritical: false,
  },
  {
    name: 'reativacao_autonoma',
    category: 'weekly',
    schedule: '0 10 * * 1',
    description: 'Reativação autônoma (segunda)',
    slaSeconds: 691200,
    isCritical: false,
  },
]

/**
 * Mapa de jobs por nome para lookup rápido.
 */
export const JOBS_BY_NAME: Record<string, JobDefinition> = Object.fromEntries(
  JOBS.map((job) => [job.name, job])
)

/**
 * Jobs críticos que devem estar sempre rodando.
 */
export const CRITICAL_JOBS = JOBS.filter((job) => job.isCritical).map((job) => job.name)

/**
 * Total de jobs configurados.
 */
export const TOTAL_JOBS = JOBS.length
```

### DoD

- [ ] Arquivo `lib/monitor/jobs-config.ts` criado
- [ ] 32 jobs definidos
- [ ] SLA correto por categoria
- [ ] Jobs críticos identificados
- [ ] Mapa JOBS_BY_NAME para lookup
- [ ] Constante TOTAL_JOBS = 32

---

## Checklist do Épico

- [ ] **S42.E02.1** - Arquivo `types/monitor.ts` criado
- [ ] **S42.E02.2** - Arquivo `lib/monitor/jobs-config.ts` criado
- [ ] Todos os tipos documentados
- [ ] 32 jobs configurados
- [ ] Sem uso de `any`
- [ ] TypeScript compila sem erros

---

## Validação

```bash
cd dashboard

# Verificar compilação de tipos
npx tsc --noEmit

# Verificar que constantes estão corretas
grep -c "name:" lib/monitor/jobs-config.ts
# Deve retornar: 32
```
