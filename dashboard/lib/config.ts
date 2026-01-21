/**
 * Dashboard Configuration - Sprint 34 E02
 *
 * Centralized configuration constants for the dashboard.
 */

/**
 * Auto-refresh intervals by priority level.
 *
 * CRITICAL: 15s - Alerts, Julia status (need immediate attention)
 * HIGH: 30s - Main metrics, funnel (important but not urgent)
 * NORMAL: 60s - Activity feed, history (informational)
 * LOW: 2min - Chips, less volatile data (background updates)
 */
export const REFRESH_INTERVALS = {
  CRITICAL: 15_000, // 15 seconds
  HIGH: 30_000, // 30 seconds
  NORMAL: 60_000, // 1 minute
  LOW: 120_000, // 2 minutes
} as const

export type RefreshPriority = keyof typeof REFRESH_INTERVALS

/**
 * Component to refresh interval mapping.
 * Documents which components use which intervals.
 */
export const COMPONENT_REFRESH_MAP: Record<string, RefreshPriority> = {
  AlertsList: 'CRITICAL',
  StatusJulia: 'CRITICAL',
  DashboardMetrics: 'HIGH',
  ConversionFunnel: 'HIGH',
  ActivityFeed: 'NORMAL',
  ChipPoolMetrics: 'LOW',
  InstanceStatusList: 'LOW',
}

/**
 * API endpoints configuration.
 */
export const API_ENDPOINTS = {
  DASHBOARD: {
    ALERTS: '/api/dashboard/alerts',
    ACTIVITY: '/api/dashboard/activity',
    METRICS: '/api/dashboard/metrics',
    FUNNEL: '/api/dashboard/funnel',
    CHIPS: '/api/dashboard/chips',
    STATUS: '/api/dashboard/status',
  },
  CAMPANHAS: '/api/campanhas',
  DIRETRIZES: '/api/diretrizes',
  HOSPITAIS: '/api/hospitais',
  ESPECIALIDADES: '/api/especialidades',
} as const

/**
 * Pagination defaults.
 */
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 10,
  MAX_PAGE_SIZE: 100,
} as const
