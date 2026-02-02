/**
 * Funções de formatação para o módulo Health Center
 */

import {
  HEALTH_STATUS_COLORS,
  HEALTH_STATUS_LABELS,
  SERVICE_STATUS_COLORS,
  ALERT_SEVERITY_COLORS,
  ALERT_SEVERITY_LABELS,
  ALERT_SEVERITY_ORDER,
  CIRCUIT_STATE_COLORS,
  PROGRESS_THRESHOLDS,
  PROGRESS_COLORS,
  GAUGE_CONFIG,
} from './constants'
import type {
  HealthStatus,
  ServiceStatusType,
  AlertSeverity,
  CircuitState,
  HealthAlert,
} from './types'

/**
 * Formata tempo em milissegundos para formato legível
 * @param ms - Tempo em milissegundos
 * @returns Tempo formatado (ex: "150ms", "2.5s", "1.5m")
 */
export function formatTempoMedio(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return '-'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${(ms / 60000).toFixed(1)}m`
}

/**
 * Calcula a cor da progress bar baseado na porcentagem
 * @param percentage - Porcentagem (0-100)
 * @returns Classe CSS de cor
 */
export function getProgressColor(percentage: number): string {
  if (percentage >= PROGRESS_THRESHOLDS.DANGER) return PROGRESS_COLORS.DANGER
  if (percentage >= PROGRESS_THRESHOLDS.WARNING) return PROGRESS_COLORS.WARNING
  return PROGRESS_COLORS.SAFE
}

/**
 * Verifica se deve exibir warning de rate limit
 * @param percentage - Porcentagem atual de uso
 * @returns true se deve exibir warning
 */
export function shouldShowRateLimitWarning(percentage: number): boolean {
  return percentage >= PROGRESS_THRESHOLDS.WARNING_DISPLAY
}

/**
 * Calcula a porcentagem de uso
 * @param used - Valor usado
 * @param limit - Valor limite
 * @returns Porcentagem arredondada (0-100)
 */
export function calculatePercentage(used: number, limit: number): number {
  if (limit <= 0) return 0
  return Math.round((used / limit) * 100)
}

/**
 * Cores padrão para status de saúde desconhecido
 */
const DEFAULT_HEALTH_COLORS = {
  stroke: '#9ca3af',
  bg: '#f3f4f6',
  text: 'text-status-neutral-foreground',
  badge: 'bg-status-neutral text-status-neutral-foreground',
}

/**
 * Cores padrão para status de serviço desconhecido
 */
const DEFAULT_SERVICE_COLORS = {
  bg: 'bg-status-neutral',
  text: 'text-status-neutral-foreground',
  icon: 'text-status-neutral-foreground',
}

/**
 * Cores padrão para severidade de alerta desconhecida
 */
const DEFAULT_ALERT_COLORS = {
  bg: 'bg-status-neutral',
  border: 'border-status-neutral',
  text: 'text-status-neutral-foreground',
  badge: 'bg-status-neutral text-status-neutral-foreground',
  icon: 'text-status-neutral-foreground',
}

/**
 * Retorna as cores para um status de saúde
 * @param status - Status de saúde
 * @returns Objeto com cores (stroke, bg, text, badge)
 */
export function getHealthStatusColors(status: HealthStatus | string) {
  if (status in HEALTH_STATUS_COLORS) {
    return HEALTH_STATUS_COLORS[status as HealthStatus]
  }
  return DEFAULT_HEALTH_COLORS
}

/**
 * Retorna o label para um status de saúde
 * @param status - Status de saúde
 * @returns Label traduzido
 */
export function getHealthStatusLabel(status: HealthStatus | string): string {
  if (status in HEALTH_STATUS_LABELS) {
    return HEALTH_STATUS_LABELS[status as HealthStatus]
  }
  return String(status).toUpperCase()
}

/**
 * Retorna as cores para um status de serviço
 * @param status - Status do serviço
 * @returns Objeto com cores (bg, text, icon)
 */
export function getServiceStatusColors(status: ServiceStatusType | string) {
  if (status in SERVICE_STATUS_COLORS) {
    return SERVICE_STATUS_COLORS[status as ServiceStatusType]
  }
  return DEFAULT_SERVICE_COLORS
}

/**
 * Retorna as cores para uma severidade de alerta
 * @param severity - Severidade do alerta
 * @returns Objeto com cores (bg, border, text, badge, icon)
 */
export function getAlertSeverityColors(severity: AlertSeverity | string) {
  if (severity in ALERT_SEVERITY_COLORS) {
    return ALERT_SEVERITY_COLORS[severity as AlertSeverity]
  }
  return DEFAULT_ALERT_COLORS
}

/**
 * Retorna o label para uma severidade de alerta
 * @param severity - Severidade do alerta
 * @returns Label traduzido
 */
export function getAlertSeverityLabel(severity: AlertSeverity | string): string {
  if (severity in ALERT_SEVERITY_LABELS) {
    return ALERT_SEVERITY_LABELS[severity as AlertSeverity]
  }
  return String(severity)
}

/**
 * Cores padrão para estados de circuit breaker desconhecidos
 */
const DEFAULT_CIRCUIT_COLORS = {
  bg: 'bg-status-neutral/50',
  border: 'border-status-neutral',
  indicator: 'bg-status-neutral-solid',
  badge: 'bg-status-neutral text-status-neutral-foreground',
}

/**
 * Retorna as cores para um estado de circuit breaker
 * @param state - Estado do circuit
 * @returns Objeto com cores (bg, border, indicator, badge)
 */
export function getCircuitStateColors(state: CircuitState | string) {
  if (state in CIRCUIT_STATE_COLORS) {
    return CIRCUIT_STATE_COLORS[state as CircuitState]
  }
  return DEFAULT_CIRCUIT_COLORS
}

/**
 * Ordena alertas por severidade (critical primeiro)
 * @param alerts - Array de alertas
 * @returns Array ordenado por severidade
 */
export function sortAlertsBySeverity<T extends { severity: AlertSeverity }>(alerts: T[]): T[] {
  return [...alerts].sort((a, b) => {
    return ALERT_SEVERITY_ORDER[a.severity] - ALERT_SEVERITY_ORDER[b.severity]
  })
}

/**
 * Conta alertas por severidade
 * @param alerts - Array de alertas
 * @returns Objeto com contagem por severidade
 */
export function countAlertsBySeverity(alerts: HealthAlert[]): Record<AlertSeverity, number> {
  return {
    critical: alerts.filter((a) => a.severity === 'critical').length,
    warn: alerts.filter((a) => a.severity === 'warn').length,
    info: alerts.filter((a) => a.severity === 'info').length,
  }
}

/**
 * Calcula o strokeDashoffset para o gauge circular
 * @param score - Score atual (0-100)
 * @returns Valor do strokeDashoffset
 */
export function calculateGaugeOffset(score: number): {
  circumference: number
  strokeDashoffset: number
} {
  const circumference = 2 * Math.PI * GAUGE_CONFIG.RADIUS
  const strokeDashoffset = circumference - (score / 100) * circumference
  return { circumference, strokeDashoffset }
}

/**
 * Formata plural para português
 * @param count - Quantidade
 * @param singular - Forma singular
 * @param plural - Forma plural (opcional, adiciona 's' por padrão)
 * @returns String formatada
 */
export function formatPlural(count: number, singular: string, plural?: string): string {
  return count === 1 ? singular : plural || `${singular}s`
}

/**
 * Determina o status de saúde baseado no score
 * @param score - Score de saúde (0-100)
 * @returns Status de saúde
 */
export function getHealthStatusFromScore(score: number): HealthStatus {
  if (score >= 80) return 'healthy'
  if (score >= 50) return 'degraded'
  return 'critical'
}

/**
 * Determina o status de serviço baseado no score
 * @param score - Score do serviço (0-100)
 * @returns Status do serviço
 */
export function getServiceStatusFromScore(score: number): ServiceStatusType {
  if (score >= 80) return 'ok'
  if (score > 50) return 'warn'
  return 'error'
}
