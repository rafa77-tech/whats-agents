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
 * Note: stroke and bg use hex values because they are used directly in SVG/canvas rendering
 */
export const HEALTH_STATUS_COLORS: Record<
  HealthStatus,
  { stroke: string; bg: string; text: string; badge: string }
> = {
  healthy: {
    stroke: '#22c55e', // green-500
    bg: '#dcfce7', // green-100
    text: 'text-status-success-foreground',
    badge: 'bg-status-success text-status-success-foreground',
  },
  degraded: {
    stroke: '#eab308', // yellow-500
    bg: '#fef9c3', // yellow-100
    text: 'text-status-warning-foreground',
    badge: 'bg-status-warning text-status-warning-foreground',
  },
  critical: {
    stroke: '#ef4444', // red-500
    bg: '#fee2e2', // red-100
    text: 'text-status-error-foreground',
    badge: 'bg-status-error text-status-error-foreground',
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
  ok: { bg: 'bg-status-success/20', text: 'text-status-success-foreground', icon: 'text-status-success-foreground' },
  warn: { bg: 'bg-status-warning/20', text: 'text-status-warning-foreground', icon: 'text-status-warning-foreground' },
  error: { bg: 'bg-status-error/20', text: 'text-status-error-foreground', icon: 'text-status-error-foreground' },
}

/**
 * Cores para severidade de alerta
 */
export const ALERT_SEVERITY_COLORS: Record<
  AlertSeverity,
  { bg: string; border: string; text: string; badge: string; icon: string }
> = {
  critical: {
    bg: 'bg-status-error/20',
    border: 'border-status-error-border',
    text: 'text-status-error-foreground',
    badge: 'bg-status-error text-status-error-foreground',
    icon: 'text-status-error-foreground',
  },
  warn: {
    bg: 'bg-status-warning/20',
    border: 'border-status-warning-border',
    text: 'text-status-warning-foreground',
    badge: 'bg-status-warning text-status-warning-foreground',
    icon: 'text-status-warning-foreground',
  },
  info: {
    bg: 'bg-status-info/20',
    border: 'border-status-info-border',
    text: 'text-status-info-foreground',
    badge: 'bg-status-info text-status-info-foreground',
    icon: 'text-status-info-foreground',
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
    bg: 'bg-status-success/10',
    border: 'border-status-success-border',
    indicator: 'bg-status-success-solid',
    badge: 'bg-status-success text-status-success-foreground',
  },
  HALF_OPEN: {
    bg: 'bg-status-warning/10',
    border: 'border-status-warning-border',
    indicator: 'bg-status-warning-solid',
    badge: 'bg-status-warning text-status-warning-foreground',
  },
  OPEN: {
    bg: 'bg-status-error/10',
    border: 'border-status-error-border',
    indicator: 'bg-status-error-solid',
    badge: 'bg-status-error text-status-error-foreground',
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
  SAFE: 'bg-status-success-solid',
  WARNING: 'bg-status-warning-solid',
  DANGER: 'bg-status-error-solid',
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
