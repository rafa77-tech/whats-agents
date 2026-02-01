/**
 * Shared formatters for dashboard module
 * Sprint 43: UX & Operação Unificada
 *
 * These functions contain business logic for formatting dashboard data.
 * Includes formatters for export (PDF/CSV) and display purposes.
 */

import type { MetricUnit, QualityUnit, DashboardPeriod } from './types'

/**
 * Formats a date string for display (DD/MM/YYYY).
 *
 * @param isoDate - ISO date string
 * @returns Formatted date in pt-BR locale
 */
export function formatExportDate(isoDate: string): string {
  return new Date(isoDate).toLocaleDateString('pt-BR')
}

/**
 * Formats a date and time for display.
 *
 * @param date - Date object
 * @returns Formatted date and time in pt-BR locale
 */
export function formatExportDateTime(date: Date): string {
  return date.toLocaleString('pt-BR')
}

/**
 * Formats a numeric value with its unit.
 *
 * @param value - Numeric value
 * @param unit - Unit type (percent, %, s, seconds, currency, or empty)
 * @returns Formatted value string
 */
export function formatValue(value: number, unit: string): string {
  if (unit === 'percent') return `${value.toFixed(1)}%`
  if (unit === '%') return `${value.toFixed(1)}%`
  if (unit === 's') return `${value}s`
  if (unit === 'seconds') return `${value}s`
  if (unit === 'currency') return `R$ ${value.toFixed(2)}`
  return value.toString()
}

/**
 * Calculates percentage change between two values.
 *
 * @param current - Current value
 * @param previous - Previous value
 * @returns Formatted change string with + or - prefix, or N/A if previous is 0
 */
export function calculateChange(current: number, previous: number): string {
  if (previous === 0) return 'N/A'
  const change = ((current - previous) / previous) * 100
  return change >= 0 ? `+${change.toFixed(0)}%` : `${change.toFixed(0)}%`
}

/**
 * Determines if a metric has reached its goal.
 *
 * @param value - Current value
 * @param meta - Target value
 * @returns 'Atingida' if value >= meta, otherwise 'Abaixo'
 */
export function getMetaStatus(value: number, meta: number): string {
  return value >= meta ? 'Atingida' : 'Abaixo'
}

/**
 * Maps chip status to display color.
 *
 * @param status - Chip status string
 * @returns Hex color code
 */
export function getStatusColor(status: string): string {
  const COLORS = {
    success: '#16a34a',
    primary: '#1e40af',
    warning: '#ca8a04',
    danger: '#dc2626',
    muted: '#6b7280',
  }

  switch (status) {
    case 'active':
      return COLORS.success
    case 'ready':
      return COLORS.primary
    case 'warming':
      return COLORS.warning
    case 'degraded':
      return COLORS.danger
    default:
      return COLORS.muted
  }
}

/**
 * Escapes a string for CSV (handles commas, quotes, and newlines).
 *
 * @param value - String to escape
 * @returns Escaped string safe for CSV
 */
export function escapeCSV(value: string): string {
  if (value.includes(',') || value.includes('"') || value.includes('\n')) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

// ============================================
// Metric Value Formatters
// ============================================

export function formatMetricValue(value: number, unit: MetricUnit): string {
  switch (unit) {
    case 'percent':
      return `${value.toFixed(1)}%`
    case 'currency':
      return new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL',
      }).format(value)
    case 'number':
    default:
      return value.toLocaleString('pt-BR')
  }
}

export function formatQualityValue(value: number, unit: QualityUnit): string {
  switch (unit) {
    case 'percent':
      return `${value.toFixed(1)}%`
    case 'seconds':
      return `${value.toFixed(1)}s`
    default:
      return String(value)
  }
}

// ============================================
// Period Formatters
// ============================================

export function formatPeriodLabel(period: DashboardPeriod): string {
  const labels: Record<DashboardPeriod, string> = {
    '7d': '7 dias',
    '14d': '14 dias',
    '30d': '30 dias',
  }
  return labels[period]
}

export function formatPeriodDates(period: DashboardPeriod): { start: Date; end: Date } {
  const end = new Date()
  const start = new Date()

  const days = parseInt(period.replace('d', ''), 10)
  start.setDate(start.getDate() - days)

  return { start, end }
}

// ============================================
// Timestamp Formatters
// ============================================

export function formatLastHeartbeat(date: Date | null): string {
  if (!date) return 'Nunca'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Agora'
  if (diffMins < 60) return `${diffMins}m atrás`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h atrás`

  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d atrás`
}

export function formatActivityTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'agora'
  if (diffMins < 60) return `${diffMins}min`

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h`

  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

// ============================================
// Rate Limit Formatters
// ============================================

export function formatRateLimit(current: number, max: number): string {
  return `${current}/${max}`
}

export function calculateRateLimitPercent(current: number, max: number): number {
  if (max === 0) return 0
  return Math.min((current / max) * 100, 100)
}

// ============================================
// Uptime Formatters
// ============================================

export function formatUptime(percentage: number): string {
  return `${percentage.toFixed(1)}%`
}

export function getUptimeStatus(percentage: number): 'good' | 'warning' | 'critical' {
  if (percentage >= 99) return 'good'
  if (percentage >= 95) return 'warning'
  return 'critical'
}
