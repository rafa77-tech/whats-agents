/**
 * Meta Types - Sprint 69
 *
 * Tipos para o módulo Meta WhatsApp Cloud API.
 */

// ============================================================================
// Template Types
// ============================================================================

export type TemplateStatus = 'APPROVED' | 'PENDING' | 'REJECTED' | 'PAUSED' | 'DISABLED'

export type TemplateCategory = 'MARKETING' | 'UTILITY' | 'AUTHENTICATION'

export interface MetaTemplate {
  id: string
  waba_id: string
  template_name: string
  category: TemplateCategory
  status: TemplateStatus
  language: string
  body_text: string
  variable_mapping: Record<string, string>
  header_format?: 'TEXT' | 'IMAGE' | 'VIDEO' | 'DOCUMENT'
  created_at: string
  updated_at: string
}

export interface MetaTemplateAnalytics {
  template_name: string
  total_sent: number
  total_delivered: number
  total_read: number
  delivery_rate: number
  read_rate: number
  cost_usd_7d: number
  quality_score?: number
}

export interface MetaTemplateWithAnalytics extends MetaTemplate {
  analytics?: MetaTemplateAnalytics
}

// ============================================================================
// Quality Types
// ============================================================================

export type MetaQualityRating = 'GREEN' | 'YELLOW' | 'RED' | 'UNKNOWN'

export interface MetaChipQuality {
  chip_id: string
  chip_nome: string
  waba_id: string
  quality_rating: MetaQualityRating
  trust_score: number
  status: string
}

export interface MetaQualityOverview {
  total: number
  green: number
  yellow: number
  red: number
  unknown: number
  chips: MetaChipQuality[]
}

export interface MetaQualityHistoryPoint {
  timestamp: string
  quality_rating: MetaQualityRating
  trust_score: number
}

// ============================================================================
// Cost Types
// ============================================================================

export interface MetaCostSummary {
  total_messages: number
  free_messages: number
  paid_messages: number
  total_cost_usd: number
  by_category: Record<string, { count: number; cost: number }>
}

export interface MetaCostByChip {
  chip_id: string
  chip_nome?: string
  total_messages: number
  total_cost_usd: number
}

export interface MetaCostByTemplate {
  template_name: string
  category: TemplateCategory
  total_sent: number
  total_cost_usd: number
}

export interface MetaDailyCost {
  date: string
  marketing: number
  utility: number
  authentication: number
  service: number
  total: number
}

export interface MetaBudgetStatus {
  waba_id: string
  daily_limit_usd: number
  daily_used_usd: number
  daily_percent: number
  weekly_limit_usd: number
  weekly_used_usd: number
  weekly_percent: number
  monthly_limit_usd: number
  monthly_used_usd: number
  monthly_percent: number
  status: 'ok' | 'warning' | 'critical' | 'blocked'
}

// ============================================================================
// Flow Types
// ============================================================================

export type FlowStatus = 'DRAFT' | 'PUBLISHED' | 'DEPRECATED' | 'BLOCKED'

export interface MetaFlow {
  id: string
  waba_id: string
  meta_flow_id: string
  name: string
  flow_type: string
  status: FlowStatus
  created_at: string
  updated_at: string
  response_count?: number
}

// ============================================================================
// API Response Types
// ============================================================================

export interface MetaDashboardResponse<T> {
  status: string
  data: T
}
