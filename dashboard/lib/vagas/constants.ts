/**
 * Constantes para o módulo de Vagas
 */

import type { ShiftStatus } from './types'

/**
 * Cores de badge por status (estilo claro para cards)
 */
export const STATUS_BADGE_COLORS: Record<ShiftStatus, string> = {
  aberta: 'bg-status-success text-status-success-foreground',
  reservada: 'bg-status-warning text-status-warning-foreground',
  confirmada: 'bg-status-info text-status-info-foreground',
  cancelada: 'bg-status-error text-status-error-foreground',
  realizada: 'bg-status-neutral text-status-neutral-foreground',
  fechada: 'bg-status-neutral text-status-neutral-foreground',
}

/**
 * Cores de indicador por status (estilo sólido para calendário)
 */
export const STATUS_INDICATOR_COLORS: Record<ShiftStatus, string> = {
  aberta: 'bg-status-success-solid',
  reservada: 'bg-status-warning-solid',
  confirmada: 'bg-status-info-solid',
  cancelada: 'bg-status-error-solid',
  realizada: 'bg-status-neutral-solid',
  fechada: 'bg-status-neutral-solid',
}

/**
 * Labels traduzidos por status
 */
export const STATUS_LABELS: Record<ShiftStatus, string> = {
  aberta: 'Aberta',
  reservada: 'Reservada',
  confirmada: 'Confirmada',
  cancelada: 'Cancelada',
  realizada: 'Realizada',
  fechada: 'Fechada',
}

/**
 * Opções de status para filtros
 */
export const STATUS_OPTIONS = [
  { value: 'aberta', label: 'Aberta' },
  { value: 'reservada', label: 'Reservada' },
  { value: 'confirmada', label: 'Confirmada' },
  { value: 'cancelada', label: 'Cancelada' },
  { value: 'realizada', label: 'Realizada' },
] as const

/**
 * Lista de todos os status possíveis
 */
export const ALL_STATUSES: ShiftStatus[] = [
  'aberta',
  'reservada',
  'confirmada',
  'cancelada',
  'realizada',
  'fechada',
]

/**
 * Dias da semana em português (abreviado)
 */
export const WEEK_DAYS = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab'] as const

/**
 * Configurações de paginação
 */
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  CALENDAR_PAGE_SIZE: 500,
} as const
