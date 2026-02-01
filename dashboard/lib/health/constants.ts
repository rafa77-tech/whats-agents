/**
 * Constantes para o módulo Health Center
 */

import type {
  HealthStatus,
  ServiceStatusType,
  AlertSeverity,
  CircuitState,
  RefreshIntervalOption,
} from './types'

/**
 * Cores para status de saúde (gauge e badges)
 */
export const HEALTH_STATUS_COLORS: Record<
  HealthStatus,
  { stroke: string; bg: string; text: string; badge: string }
> = {
  healthy: {
    stroke: '#22c55e',
    bg: '#dcfce7',
    text: 'text-green-600',
    badge: 'bg-green-100 text-green-800',
  },
  degraded: {
    stroke: '#eab308',
    bg: '#fef9c3',
    text: 'text-yellow-600',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  critical: {
    stroke: '#ef4444',
    bg: '#fee2e2',
    text: 'text-red-600',
    badge: 'bg-red-100 text-red-800',
  },
}

/**
 * Labels para status de saúde
 */
export const HEALTH_STATUS_LABELS: Record<HealthStatus, string> = {
  healthy: 'HEALTHY',
  degraded: 'DEGRADED',
  critical: 'CRITICAL',
}

/**
 * Cores para status de serviço
 */
export const SERVICE_STATUS_COLORS: Record<
  ServiceStatusType,
  { bg: string; text: string; icon: string }
> = {
  ok: { bg: 'bg-green-50', text: 'text-green-800', icon: 'text-green-600' },
  warn: { bg: 'bg-yellow-50', text: 'text-yellow-800', icon: 'text-yellow-600' },
  error: { bg: 'bg-red-50', text: 'text-red-800', icon: 'text-red-600' },
}

/**
 * Cores para severidade de alerta
 */
export const ALERT_SEVERITY_COLORS: Record<
  AlertSeverity,
  { bg: string; border: string; text: string; badge: string; icon: string }
> = {
  critical: {
    bg: 'bg-red-50',
    border: 'border-red-200',
    text: 'text-red-600',
    badge: 'bg-red-100 text-red-800',
    icon: 'text-red-500',
  },
  warn: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-200',
    text: 'text-yellow-600',
    badge: 'bg-yellow-100 text-yellow-800',
    icon: 'text-yellow-500',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-200',
    text: 'text-blue-600',
    badge: 'bg-blue-100 text-blue-800',
    icon: 'text-blue-500',
  },
}

/**
 * Labels para severidade de alerta
 */
export const ALERT_SEVERITY_LABELS: Record<AlertSeverity, string> = {
  critical: 'Critico',
  warn: 'Alerta',
  info: 'Info',
}

/**
 * Ordem de prioridade para severidade (menor = maior prioridade)
 */
export const ALERT_SEVERITY_ORDER: Record<AlertSeverity, number> = {
  critical: 0,
  warn: 1,
  info: 2,
}

/**
 * Cores para estado do circuit breaker
 */
export const CIRCUIT_STATE_COLORS: Record<
  CircuitState,
  { bg: string; border: string; indicator: string; badge: string }
> = {
  CLOSED: {
    bg: 'bg-green-50/50',
    border: 'border-green-200',
    indicator: 'bg-green-500',
    badge: 'bg-green-100 text-green-800',
  },
  HALF_OPEN: {
    bg: 'bg-yellow-50/50',
    border: 'border-yellow-200',
    indicator: 'bg-yellow-500',
    badge: 'bg-yellow-100 text-yellow-800',
  },
  OPEN: {
    bg: 'bg-red-50/50',
    border: 'border-red-200',
    indicator: 'bg-red-500',
    badge: 'bg-red-100 text-red-800',
  },
}

/**
 * Legenda dos estados de circuit breaker
 */
export const CIRCUIT_STATE_LEGEND = 'CLOSED = operacional | HALF_OPEN = testando | OPEN = bloqueado'

/**
 * Intervalos de refresh disponíveis
 */
export const REFRESH_INTERVALS: RefreshIntervalOption[] = [
  { label: '15s', value: 15000 },
  { label: '30s', value: 30000 },
  { label: '60s', value: 60000 },
  { label: 'Off', value: 0 },
]

/**
 * Intervalo de refresh padrão (30s)
 */
export const DEFAULT_REFRESH_INTERVAL = 30000

/**
 * Configuração padrão de rate limit
 */
export const DEFAULT_RATE_LIMIT = {
  hourly: { used: 0, limit: 20 },
  daily: { used: 0, limit: 100 },
}

/**
 * Thresholds para cores de progress bar
 */
export const PROGRESS_THRESHOLDS = {
  WARNING: 70,
  DANGER: 90,
  WARNING_DISPLAY: 80, // Quando mostrar mensagem de warning
}

/**
 * Cores para progress bar por percentual
 */
export const PROGRESS_COLORS = {
  SAFE: 'bg-green-500',
  WARNING: 'bg-yellow-500',
  DANGER: 'bg-red-500',
}

/**
 * Configuração do gauge (círculo de progresso)
 */
export const GAUGE_CONFIG = {
  RADIUS: 45,
  STROKE_WIDTH: 8,
  BACKGROUND_STROKE: '#e5e7eb',
  TRANSITION_DURATION: 500,
}

/**
 * Número máximo de alertas exibidos no painel
 */
export const MAX_DISPLAYED_ALERTS = 5

/**
 * Lista de serviços padrão quando API não retorna dados
 */
export const DEFAULT_SERVICES = [
  { name: 'WhatsApp', status: 'warn' as const },
  { name: 'Redis', status: 'warn' as const },
  { name: 'Supabase', status: 'ok' as const },
  { name: 'LLM', status: 'ok' as const },
]

/**
 * Circuit breakers padrão quando API não retorna dados
 */
export const DEFAULT_CIRCUITS = [
  { name: 'evolution', state: 'CLOSED' as const, failures: 0, threshold: 5 },
  { name: 'claude', state: 'CLOSED' as const, failures: 0, threshold: 5 },
  { name: 'supabase', state: 'CLOSED' as const, failures: 0, threshold: 5 },
]
