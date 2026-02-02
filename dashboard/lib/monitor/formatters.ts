/**
 * Formatadores para o modulo Monitor
 * Sprint 43: UX & Operacao Unificada
 */

import type { JobStatus, SystemHealthStatus } from './types'
import { JOB_STATUS_LABELS, SYSTEM_HEALTH_LABELS } from './constants'

// ============================================
// Status Formatters
// ============================================

export function formatJobStatus(status: JobStatus): string {
  return JOB_STATUS_LABELS[status] || status
}

export function formatSystemHealth(status: SystemHealthStatus): string {
  return SYSTEM_HEALTH_LABELS[status] || status
}

// ============================================
// Duration Formatters
// ============================================

export function formatDuration(ms: number | null): string {
  if (ms === null) return '—'

  if (ms < 1000) return ms + 'ms'

  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return seconds + 's'

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60
  if (minutes < 60) {
    return remainingSeconds > 0 ? minutes + 'm ' + remainingSeconds + 's' : minutes + 'm'
  }

  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60
  return hours + 'h ' + remainingMinutes + 'm'
}

export function formatDurationShort(ms: number): string {
  if (ms < 1000) return '<1s'
  const seconds = Math.floor(ms / 1000)
  if (seconds < 60) return seconds + 's'
  const minutes = Math.floor(seconds / 60)
  return minutes + 'm'
}

// ============================================
// Time Formatters
// ============================================

export function formatLastRun(timestamp: string | null): string {
  if (!timestamp) return 'Nunca'

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return 'Agora'
  if (diffMins < 60) return diffMins + ' min'

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return diffHours + 'h'

  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
}

export function formatNextRun(timestamp: string | null): string {
  if (!timestamp) return '—'

  const date = new Date(timestamp)
  const now = new Date()
  const diffMs = date.getTime() - now.getTime()

  if (diffMs <= 0) return 'Agora'

  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 60) return 'em ' + diffMins + ' min'

  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return 'em ' + diffHours + 'h'

  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// ============================================
// Rate Formatters
// ============================================

export function formatSuccessRate(success: number, total: number): string {
  if (total === 0) return '—'
  const rate = (success / total) * 100
  return rate.toFixed(0) + '%'
}

export function calculateSuccessRate(success: number, total: number): number {
  if (total === 0) return 0
  return (success / total) * 100
}

// ============================================
// Schedule Formatters
// ============================================

export function describeCron(cron: string): string {
  const parts = cron.split(' ')
  if (parts.length !== 5) return cron

  const [minute, hour, dayMonth, month, dayWeek] = parts

  // Every minute
  if (cron === '* * * * *') return 'A cada minuto'

  // Every N minutes
  if (minute?.startsWith('*/') && hour === '*') {
    const n = minute.replace('*/', '')
    return 'A cada ' + n + ' minutos'
  }

  // Every hour
  if (minute === '0' && hour === '*') return 'A cada hora'

  // Every N hours
  if (hour?.startsWith('*/') && minute === '0') {
    const n = hour.replace('*/', '')
    return 'A cada ' + n + ' horas'
  }

  // Specific time daily
  if (hour && minute && dayMonth === '*' && month === '*' && dayWeek === '*') {
    return 'Diario as ' + hour + ':' + minute.padStart(2, '0')
  }

  return cron
}

// ============================================
// Health Score Formatters
// ============================================

export function formatHealthScore(score: number): string {
  return score.toFixed(0) + '%'
}

export function getHealthScoreColor(score: number): string {
  if (score >= 80) return 'text-status-success-solid'
  if (score >= 50) return 'text-status-warning-solid'
  return 'text-status-error-solid'
}
