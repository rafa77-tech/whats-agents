/**
 * Tipos centralizados para o módulo Dashboard
 * Sprint 43: UX & Operação Unificada
 *
 * Re-exporta tipos de types/dashboard.ts e adiciona tipos adicionais
 */

// Re-export all types from types/dashboard.ts
export * from '@/types/dashboard'

// ============================================
// Additional Dashboard Types
// ============================================

export interface DashboardState {
  isLoading: boolean
  isRefreshing: boolean
  error: string | null
}

export interface DashboardDataState {
  metricsData: import('@/types/dashboard').MetricData[]
  qualityData: import('@/types/dashboard').QualityMetricData[]
  operationalData: import('@/types/dashboard').OperationalStatusData
  chipPoolData: import('@/types/dashboard').ChipPoolOverviewData | null
  chipsList: import('@/types/dashboard').ChipDetail[]
  funnelData: import('@/types/dashboard').FunnelDataVisual
  trendsData: import('@/types/dashboard').TrendsData
  alertsData: import('@/types/dashboard').AlertsData
  activityData: import('@/types/dashboard').ActivityFeedData
}

export interface DashboardHeaderState {
  juliaStatus: 'online' | 'offline' | 'degraded'
  lastHeartbeat: Date | null
  uptime30d: number
}

// ============================================
// API Response Types
// ============================================

export interface DashboardMetricsResponse {
  metrics: {
    responseRate: { value: number; previous: number; meta: number }
    conversionRate: { value: number; previous: number; meta: number }
    closingsPerWeek: { value: number; previous: number; meta: number }
  }
}

export interface DashboardQualityResponse {
  metrics: {
    botDetection: { value: number; previous: number }
    avgLatency: { value: number; previous: number }
    handoffRate: { value: number; previous: number }
  }
}

export interface DashboardStatusResponse {
  status: 'online' | 'offline' | 'degraded'
  lastHeartbeat: string | null
  uptime30d: number
}
