/**
 * Types for Health Center - Sprint 43
 */

export interface HealthScoreResponse {
  score: number
  status: 'healthy' | 'degraded' | 'critical'
  components: {
    name: string
    score: number
    maxScore: number
    status: 'ok' | 'warn' | 'error'
  }[]
  recommendations: string[]
  lastUpdated: string
}

export interface HealthAlertResponse {
  id: string
  tipo: string
  severity: 'info' | 'warn' | 'critical'
  message: string
  source: string
  createdAt: string
  resolved: boolean
}

export interface CircuitBreakerStatus {
  name: string
  state: 'CLOSED' | 'HALF_OPEN' | 'OPEN'
  failures: number
  threshold: number
  lastFailure: string | null
  lastReset: string | null
}

export interface CircuitHistoryEntry {
  timestamp: string
  circuit: string
  fromState: string
  toState: string
  reason: string
}

export interface RateLimitStats {
  hourly: {
    used: number
    limit: number
    percentage: number
  }
  daily: {
    used: number
    limit: number
    percentage: number
  }
  history: {
    hour: string
    count: number
  }[]
}

export interface QueueStats {
  pendentes: number
  processando: number
  processadasHora: number
  tempoMedioEspera: number
  maiorEsperaAtual: number
}

export interface ServiceStatus {
  name: string
  status: 'ok' | 'warn' | 'error'
  latency?: number
  lastCheck: string
}

export interface HealthOverviewResponse {
  score: HealthScoreResponse
  alerts: HealthAlertResponse[]
  circuits: CircuitBreakerStatus[]
  rateLimit: RateLimitStats
  queue: QueueStats
  services: ServiceStatus[]
  timestamp: string
}
