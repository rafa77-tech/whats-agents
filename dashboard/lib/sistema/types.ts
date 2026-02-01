/**
 * Tipos centralizados para o módulo Sistema
 * Sprint 43: UX & Operação Unificada
 */

// ============================================
// Tipos de Status do Sistema
// ============================================

export interface AutonomousFeatures {
  discovery_automatico: boolean
  oferta_automatica: boolean
  reativacao_automatica: boolean
  feedback_automatico: boolean
}

export interface SystemStatus {
  pilot_mode: boolean
  autonomous_features: AutonomousFeatures
  last_changed_by?: string
  last_changed_at?: string
}

// ============================================
// Tipos de Configuração
// ============================================

export interface RateLimitConfig {
  msgs_por_hora: number
  msgs_por_dia: number
  intervalo_min: number
  intervalo_max: number
}

export interface ScheduleConfig {
  inicio: number
  fim: number
  dias: string
}

export interface ScheduleConfigEdit {
  inicio: number
  fim: number
  dias: string[]
}

export interface UsageStats {
  msgs_hora: number
  msgs_dia: number
  horario_permitido: boolean
  hora_atual: string
}

export interface SystemConfig {
  rate_limit: RateLimitConfig
  horario: ScheduleConfig
  uso_atual?: UsageStats
}

// ============================================
// Tipos de Features
// ============================================

export type FeatureKey =
  | 'discovery_automatico'
  | 'oferta_automatica'
  | 'reativacao_automatica'
  | 'feedback_automatico'

export const VALID_FEATURES: readonly FeatureKey[] = [
  'discovery_automatico',
  'oferta_automatica',
  'reativacao_automatica',
  'feedback_automatico',
] as const

export interface FeatureInfo {
  title: string
  description: string
}

export const FEATURE_INFO: Record<FeatureKey, FeatureInfo> = {
  discovery_automatico: {
    title: 'Discovery Automatico',
    description: 'Conhecer medicos nao-enriquecidos',
  },
  oferta_automatica: {
    title: 'Oferta Automatica',
    description: 'Ofertar vagas com furo de escala',
  },
  reativacao_automatica: {
    title: 'Reativacao Automatica',
    description: 'Retomar contato com inativos',
  },
  feedback_automatico: {
    title: 'Feedback Automatico',
    description: 'Pedir feedback pos-plantao',
  },
}

// ============================================
// Tipos de Request/Response
// ============================================

export interface PilotModeRequest {
  pilot_mode: boolean
  safe_mode?: boolean
  motivo?: string
}

export interface FeatureToggleRequest {
  enabled: boolean
}

export interface FeatureToggleResponse {
  success: boolean
  feature: string
  enabled: boolean
  pilot_mode: boolean
  autonomous_features: Record<string, boolean>
}

export interface UpdateConfigRequest {
  rate_limit?: RateLimitConfig
  horario?: ScheduleConfigEdit
}

// ============================================
// Tipos de Estado de UI
// ============================================

export type ConfirmDialogState = 'enable' | 'disable' | null

export interface FeatureDialogState {
  feature: FeatureKey
  action: 'enable' | 'disable'
}

// ============================================
// Tipos de Backend
// ============================================

export interface RateLimitStats {
  msgs_hora: number
  limite_hora: number
  msgs_dia: number
  limite_dia: number
  horario_permitido: boolean
  hora_atual: string
  dia_semana: string
}

export interface RateLimitBackendResponse {
  rate_limit: RateLimitStats
  timestamp: string
}
