/**
 * Constantes para o modulo Monitor
 * Sprint 43: UX & Operacao Unificada
 */

import type {
  JobStatus,
  JobCategory,
  SystemHealthStatus,
  JobStatusFilter,
  TimeRangeFilter,
} from './types'

// ============================================
// Status Labels and Colors
// ============================================

export const JOB_STATUS_LABELS: Record<JobStatus, string> = {
  running: 'Executando',
  success: 'Sucesso',
  error: 'Erro',
  timeout: 'Timeout',
}

export const JOB_STATUS_COLORS: Record<JobStatus, string> = {
  running: 'bg-status-info text-status-info-foreground',
  success: 'bg-status-success text-status-success-foreground',
  error: 'bg-status-error text-status-error-foreground',
  timeout: 'bg-status-warning text-status-warning-foreground',
}

export const SYSTEM_HEALTH_LABELS: Record<SystemHealthStatus, string> = {
  healthy: 'Saudavel',
  degraded: 'Degradado',
  critical: 'Critico',
}

export const SYSTEM_HEALTH_COLORS: Record<SystemHealthStatus, string> = {
  healthy: 'text-status-success-solid',
  degraded: 'text-status-warning-solid',
  critical: 'text-status-error-solid',
}

// ============================================
// Category Labels
// ============================================

export const JOB_CATEGORY_LABELS: Record<JobCategory, string> = {
  critical: 'Critico',
  frequent: 'Frequente',
  hourly: 'Horario',
  daily: 'Diario',
  weekly: 'Semanal',
}

// ============================================
// Filter Options
// ============================================

export const STATUS_FILTER_OPTIONS: { value: JobStatusFilter; label: string }[] = [
  { value: 'all', label: 'Todos' },
  { value: 'running', label: 'Executando' },
  { value: 'success', label: 'Sucesso' },
  { value: 'error', label: 'Erro' },
  { value: 'timeout', label: 'Timeout' },
  { value: 'stale', label: 'Atrasado' },
]

export const TIME_RANGE_OPTIONS: { value: TimeRangeFilter; label: string }[] = [
  { value: '1h', label: 'Ultima hora' },
  { value: '6h', label: 'Ultimas 6h' },
  { value: '24h', label: 'Ultimas 24h' },
]

export const CATEGORY_FILTER_OPTIONS: { value: JobCategory | 'all'; label: string }[] = [
  { value: 'all', label: 'Todas' },
  { value: 'critical', label: 'Critico' },
  { value: 'frequent', label: 'Frequente' },
  { value: 'hourly', label: 'Horario' },
  { value: 'daily', label: 'Diario' },
  { value: 'weekly', label: 'Semanal' },
]

// ============================================
// Default Values
// ============================================

export const DEFAULT_FILTERS = {
  status: 'all' as JobStatusFilter,
  timeRange: '24h' as TimeRangeFilter,
  search: '',
  category: 'all' as const,
}

export const DEFAULT_TABLE_SORT = {
  column: 'lastRun' as const,
  direction: 'desc' as const,
}
