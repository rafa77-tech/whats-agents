/**
 * Constantes para o modulo Monitor
 * Sprint 43: UX & Operacao Unificada
 */

import type { JobStatus, JobCategory, SystemHealthStatus, JobStatusFilter, TimeRangeFilter } from './types'

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
  running: 'bg-blue-100 text-blue-800',
  success: 'bg-green-100 text-green-800',
  error: 'bg-red-100 text-red-800',
  timeout: 'bg-yellow-100 text-yellow-800',
}

export const SYSTEM_HEALTH_LABELS: Record<SystemHealthStatus, string> = {
  healthy: 'Saudavel',
  degraded: 'Degradado',
  critical: 'Critico',
}

export const SYSTEM_HEALTH_COLORS: Record<SystemHealthStatus, string> = {
  healthy: 'text-green-600',
  degraded: 'text-yellow-600',
  critical: 'text-red-600',
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
