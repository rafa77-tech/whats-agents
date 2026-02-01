/**
 * Tipos para o modulo de Auditoria
 */

import type { LucideIcon } from 'lucide-react'

// =============================================================================
// Tipos de acao
// =============================================================================

/**
 * Tipos de acoes de auditoria disponiveis
 */
export type AuditAction =
  | 'julia_toggle'
  | 'julia_pause'
  | 'feature_flag_update'
  | 'rate_limit_update'
  | 'manual_handoff'
  | 'return_to_julia'
  | 'circuit_reset'
  | 'create_campaign'
  | 'start_campaign'
  | 'pause_campaign'

// =============================================================================
// Interfaces de dados
// =============================================================================

/**
 * Log de auditoria
 */
export interface AuditLog {
  id: string
  action: string
  actor_email: string
  actor_role: string
  details: Record<string, unknown>
  created_at: string
}

/**
 * Filtros de busca de logs
 */
export interface AuditFilters {
  action?: string | undefined
  actor_email?: string | undefined
  from_date?: string | undefined
  to_date?: string | undefined
}

/**
 * Resposta da API de auditoria
 */
export interface AuditResponse {
  data: AuditLog[]
  total: number
  page: number
  per_page: number
  pages: number
}

// =============================================================================
// Interfaces de props de componentes
// =============================================================================

/**
 * Props do componente AuditList
 */
export interface AuditListProps {
  logs: AuditLog[]
  total: number
  page: number
  pages: number
  onPageChange: (page: number) => void
}

/**
 * Props do componente AuditItem
 */
export interface AuditItemProps {
  log: AuditLog
}

/**
 * Props do componente AuditFilters
 */
export interface AuditFiltersProps {
  filters: AuditFilters
  onApply: (filters: AuditFilters) => void
  onClear: () => void
}

// =============================================================================
// Interfaces de retorno de hooks
// =============================================================================

/**
 * Retorno do hook useAuditLogs
 */
export interface UseAuditLogsReturn {
  data: AuditResponse | null
  loading: boolean
  error: string | null
  filters: AuditFilters
  page: number
  searchInput: string
  actions: {
    setFilters: (filters: AuditFilters) => void
    setPage: (page: number) => void
    setSearch: (search: string) => void
    clearFilters: () => void
    refresh: () => Promise<void>
    exportLogs: () => Promise<void>
  }
}

// =============================================================================
// Tipos auxiliares
// =============================================================================

/**
 * Mapeamento de acao para icone
 */
export type ActionIconMap = Record<string, LucideIcon>

/**
 * Mapeamento de acao para label
 */
export type ActionLabelMap = Record<string, string>

/**
 * Opcao de acao para select
 */
export interface ActionOption {
  value: string
  label: string
}
