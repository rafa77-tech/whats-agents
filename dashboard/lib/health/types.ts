/**
 * Types para o módulo Health Center
 * Re-exporta e estende tipos de types/health.ts
 */

// Re-export from centralized types
export type {
  HealthScoreResponse,
  HealthAlertResponse,
  CircuitBreakerStatus,
  CircuitHistoryEntry,
  RateLimitStats,
  QueueStats,
  ServiceStatus,
  HealthOverviewResponse,
} from '@/types/health'

/**
 * Status geral de saúde do sistema
 */
export type HealthStatus = 'healthy' | 'degraded' | 'critical'

/**
 * Status de serviço
 */
export type ServiceStatusType = 'ok' | 'warn' | 'error'

/**
 * Severidade de alerta
 */
export type AlertSeverity = 'info' | 'warn' | 'critical'

/**
 * Estado do circuit breaker
 */
export type CircuitState = 'CLOSED' | 'HALF_OPEN' | 'OPEN'

/**
 * Alerta de saúde (versão simplificada para componentes)
 */
export interface HealthAlert {
  id: string
  tipo: string
  severity: AlertSeverity
  message: string
  source: string
}

/**
 * Circuit breaker (versão simplificada para componentes)
 */
export interface Circuit {
  name: string
  state: CircuitState
  failures: number
  threshold: number
}

/**
 * Status de serviço (versão simplificada para componentes)
 */
export interface Service {
  name: string
  status: ServiceStatusType
}

/**
 * Dados de rate limit
 */
export interface RateLimitData {
  hourly: { used: number; limit: number }
  daily: { used: number; limit: number }
}

/**
 * Dados da fila de mensagens
 */
export interface QueueData {
  pendentes: number
  processando: number
  processadasPorHora?: number
  tempoMedioMs?: number | null
}

/**
 * Dados consolidados de saúde
 */
export interface HealthData {
  score: number
  status: HealthStatus
  alerts: HealthAlert[]
  circuits: Circuit[]
  services: Service[]
  rateLimit: RateLimitData
  queue: QueueData
}

/**
 * Opção de intervalo de refresh
 */
export interface RefreshIntervalOption {
  label: string
  value: number
}
