/**
 * Tipos centralizados para o módulo Chips
 * Sprint 43: UX & Operação Unificada
 *
 * Re-exporta tipos de types/chips.ts e adiciona tipos adicionais
 */

// Re-export all types from types/chips.ts
export * from '@/types/chips'

// ============================================
// Additional Chips Types
// ============================================

export interface ChipsPageState {
  isLoading: boolean
  isRefreshing: boolean
  error: string | null
}

export interface ChipsFiltersState {
  search: string
  status: import('@/types/chips').ChipListItem['status'] | null
  trustLevel: import('@/types/chips').TrustLevelExtended | null
  warmupPhase: import('@/types/chips').WarmupPhase | null
  hasAlert: boolean | null
  sortBy: import('@/types/chips').ChipsListParams['sortBy']
  order: 'asc' | 'desc'
}

export interface ChipsPaginationState {
  page: number
  pageSize: number
  total: number
  hasMore: boolean
}
