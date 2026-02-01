/**
 * Tipos centralizados para o módulo Metricas
 * Sprint 43: UX & Operação Unificada
 */

// ============================================
// Tipos de Date Range
// ============================================

export interface DateRange {
  from: Date
  to: Date
}

// ============================================
// Tipos de KPIs
// ============================================

export interface KPIMetric {
  label: string
  value: string
  change: number
  changeLabel: string
}

export interface KPIs {
  total_messages: KPIMetric
  active_doctors: KPIMetric
  conversion_rate: KPIMetric
  avg_response_time: KPIMetric
}

// ============================================
// Tipos de Funnel
// ============================================

export interface FunnelStage {
  name: string
  count: number
  percentage: number
  color: string
}

// ============================================
// Tipos de Trends
// ============================================

export interface TrendPoint {
  date: string
  messages: number
  conversions: number
}

// ============================================
// Tipos de Response Time
// ============================================

export interface ResponseTimePoint {
  hour: string
  avg_time_seconds: number
  count: number
}

// ============================================
// Tipos Agregados
// ============================================

export interface MetricsData {
  kpis: KPIs
  funnel: FunnelStage[]
  trends: TrendPoint[]
  response_times: ResponseTimePoint[]
}

// ============================================
// Tipos de Request/Response
// ============================================

export interface MetricsQueryParams {
  from?: string
  to?: string
}

export interface ExportResponse {
  content: string
  filename: string
}
