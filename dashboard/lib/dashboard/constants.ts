/**
 * Constantes para o módulo Dashboard
 * Sprint 43: UX & Operação Unificada
 */

import type {
  DashboardPeriod,
  OperationalStatusData,
  FunnelDataVisual,
  TrendsData,
  AlertsData,
  ActivityFeedData,
} from './types'

// ============================================
// Period Constants
// ============================================

export const DASHBOARD_PERIODS: DashboardPeriod[] = ['7d', '14d', '30d']

export const PERIOD_LABELS: Record<DashboardPeriod, string> = {
  '7d': '7 dias',
  '14d': '14 dias',
  '30d': '30 dias',
}

// ============================================
// Default States
// ============================================

export const DEFAULT_OPERATIONAL_STATUS: OperationalStatusData = {
  rateLimitHour: { current: 0, max: 20, label: 'Rate Limit Hora' },
  rateLimitDay: { current: 0, max: 100, label: 'Rate Limit Dia' },
  queueSize: 0,
  llmUsage: { haiku: 80, sonnet: 20 },
  instances: [],
}

export const DEFAULT_FUNNEL: FunnelDataVisual = {
  stages: [
    { id: 'enviadas', label: 'Enviadas', count: 0, previousCount: 0, percentage: 100 },
    { id: 'entregues', label: 'Entregues', count: 0, previousCount: 0, percentage: 0 },
    { id: 'respostas', label: 'Respostas', count: 0, previousCount: 0, percentage: 0 },
    { id: 'interesse', label: 'Interesse', count: 0, previousCount: 0, percentage: 0 },
    { id: 'fechadas', label: 'Fechadas', count: 0, previousCount: 0, percentage: 0 },
  ],
  period: '7 dias',
}

export const DEFAULT_TRENDS: TrendsData = {
  metrics: [],
  period: '7d',
}

export const DEFAULT_ALERTS: AlertsData = {
  alerts: [],
  totalCritical: 0,
  totalWarning: 0,
}

export const DEFAULT_ACTIVITY: ActivityFeedData = {
  events: [],
  hasMore: false,
}

// ============================================
// Metric Configuration
// ============================================

export const METRIC_CONFIG = {
  responseRate: {
    label: 'Taxa de Resposta',
    unit: 'percent' as const,
    metaOperator: 'gt' as const,
  },
  conversionRate: {
    label: 'Taxa de Conversão',
    unit: 'percent' as const,
    metaOperator: 'gt' as const,
  },
  closingsPerWeek: {
    label: 'Fechamentos/Semana',
    unit: 'number' as const,
    metaOperator: 'gt' as const,
  },
} as const

export const QUALITY_CONFIG = {
  botDetection: {
    label: 'Detecção Bot',
    unit: 'percent' as const,
    threshold: { good: 1, warning: 5 },
    operator: 'lt' as const,
    tooltip: 'Taxa de mensagens detectadas como bot',
  },
  avgLatency: {
    label: 'Latência Média',
    unit: 'seconds' as const,
    threshold: { good: 30, warning: 60 },
    operator: 'lt' as const,
    tooltip: 'Tempo médio de resposta',
  },
  handoffRate: {
    label: 'Taxa Handoff',
    unit: 'percent' as const,
    threshold: { good: 5, warning: 15 },
    operator: 'lt' as const,
    tooltip: 'Taxa de transferência para humano',
  },
} as const

// ============================================
// Status Colors
// ============================================

export const JULIA_STATUS_COLORS = {
  online: 'text-status-success-solid bg-status-success',
  offline: 'text-status-error-solid bg-status-error',
  degraded: 'text-status-warning-solid bg-status-warning',
} as const

export const ALERT_SEVERITY_COLORS = {
  critical: 'bg-status-error text-status-error-foreground border-status-error-border',
  warning: 'bg-status-warning text-status-warning-foreground border-status-warning-border',
  info: 'bg-status-info text-status-info-foreground border-status-info-border',
} as const
