/**
 * Monitor Types - Sprint 42
 *
 * Tipos para a pagina de monitoramento de jobs e saude do sistema.
 */

// ============================================================================
// Job Status Types
// ============================================================================

/**
 * Status de execucao de um job.
 * - running: Job esta executando
 * - success: Job completou com sucesso
 * - error: Job falhou com erro
 * - timeout: Job excedeu timeout (300s)
 */
export type JobStatus = 'running' | 'success' | 'error' | 'timeout'

/**
 * Categoria de job baseada na frequencia de execucao.
 * Usado para agrupamento visual e calculo de SLA.
 */
export type JobCategory = 'critical' | 'frequent' | 'hourly' | 'daily' | 'weekly'

/**
 * Definicao estatica de um job do sistema.
 * Baseado na lista JOBS de app/workers/scheduler.py.
 */
export interface JobDefinition {
  /** Nome unico do job (ex: "heartbeat", "processar_mensagens_agendadas") */
  name: string
  /** Nome amigavel para exibicao na UI */
  displayName: string
  /** Categoria do job para agrupamento */
  category: JobCategory
  /** Expressao cron do schedule (ex: "* * * * *") */
  schedule: string
  /** Descricao legivel do job */
  description: string
  /** SLA em segundos (tempo maximo entre execucoes) */
  slaSeconds: number
  /** Se e um job critico (deve estar sempre rodando) */
  isCritical: boolean
}

/**
 * Registro de uma execucao de job.
 * Mapeado da tabela job_executions do Supabase.
 */
export interface JobExecution {
  /** UUID da execucao */
  id: string
  /** Nome do job */
  jobName: string
  /** Timestamp de inicio (ISO 8601) */
  startedAt: string
  /** Timestamp de fim (ISO 8601), null se ainda executando */
  finishedAt: string | null
  /** Status da execucao */
  status: JobStatus
  /** Duracao em milissegundos, null se ainda executando */
  durationMs: number | null
  /** Codigo HTTP da resposta, null se nao aplicavel */
  responseCode: number | null
  /** Mensagem de erro (truncada 500 chars), null se sucesso */
  error: string | null
  /** Numero de itens processados, null se nao reportado */
  itemsProcessed: number | null
}

/**
 * Resumo agregado de um job para exibicao na tabela.
 * Calculado a partir de multiplas execucoes.
 */
export interface JobSummary {
  /** Nome do job */
  name: string
  /** Nome amigavel para exibicao na UI */
  displayName: string
  /** Categoria do job */
  category: JobCategory
  /** Expressao cron */
  schedule: string
  /** Descricao humanizada do schedule */
  scheduleDescription: string
  /** Descricao do job */
  description: string
  /** Timestamp da ultima execucao */
  lastRun: string | null
  /** Status da ultima execucao */
  lastStatus: JobStatus | null
  /** Timestamp esperado da proxima execucao */
  nextExpectedRun: string | null
  /** Total de execucoes nas ultimas 24h */
  runs24h: number
  /** Execucoes com sucesso nas ultimas 24h */
  success24h: number
  /** Execucoes com erro nas ultimas 24h */
  errors24h: number
  /** Execucoes com timeout nas ultimas 24h */
  timeouts24h: number
  /** Duracao media em ms */
  avgDurationMs: number
  /** Total de itens processados nas ultimas 24h */
  totalItemsProcessed: number
  /** Ultimo erro (se houver) */
  lastError: string | null
  /** SLA em segundos */
  slaSeconds: number
  /** Se esta atrasado (excedeu SLA) */
  isStale: boolean
  /** Segundos desde ultima execucao */
  secondsSinceLastRun: number | null
  /** Se e um job critico */
  isCritical: boolean
}

// ============================================================================
// System Health Types
// ============================================================================

/**
 * Status geral de saude do sistema.
 */
export type SystemHealthStatus = 'healthy' | 'degraded' | 'critical'

/**
 * Dados de saude do sistema.
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
  /** Ultima atualizacao */
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
  /** Dados de saude do sistema */
  systemHealth: SystemHealthData
  /** Estatisticas agregadas dos jobs */
  jobsStats: {
    /** Total de jobs configurados */
    totalJobs: number
    /** Taxa de sucesso nas ultimas 24h (0-100) */
    successRate24h: number
    /** Numero de jobs que falharam nas ultimas 24h */
    failedJobs24h: number
    /** Numero de jobs executando agora */
    runningJobs: number
    /** Numero de jobs atrasados (stale) */
    staleJobs: number
  }
  /** Alertas ativos */
  alerts: {
    /** Jobs criticos atrasados */
    criticalStale: string[]
    /** Jobs com erros nas ultimas 24h */
    jobsWithErrors: string[]
    /** Jobs com timeouts nas ultimas 24h */
    jobsWithTimeouts: string[]
    /** Jobs criticos que nunca executaram */
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
  /** Periodo consultado */
  period: string
  /** Timestamp da resposta */
  timestamp: string
}

/**
 * Resposta de GET /api/dashboard/monitor/job/[name]/executions
 * Historico de execucoes de um job especifico.
 */
export interface JobExecutionsResponse {
  /** Nome do job */
  jobName: string
  /** Lista de execucoes */
  executions: JobExecution[]
  /** Total de execucoes (para paginacao) */
  total: number
  /** Pagina atual */
  page: number
  /** Tamanho da pagina */
  pageSize: number
  /** Se ha mais paginas */
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
 * Filtro de periodo de tempo.
 */
export type TimeRangeFilter = '1h' | '6h' | '24h'

/**
 * Estado dos filtros na pagina.
 */
export interface MonitorFilters {
  /** Filtro de status */
  status: JobStatusFilter
  /** Filtro de periodo */
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
 * Estado de ordenacao da tabela.
 */
export interface JobsTableSort {
  /** Coluna de ordenacao */
  column: 'name' | 'lastRun' | 'status' | 'duration' | 'successRate'
  /** Direcao */
  direction: 'asc' | 'desc'
}

/**
 * Props do modal de detalhes do job.
 */
export interface JobDetailModalProps {
  /** Se o modal esta aberto */
  open: boolean
  /** Callback para fechar */
  onOpenChange: (open: boolean) => void
  /** Nome do job selecionado */
  jobName: string | null
}
