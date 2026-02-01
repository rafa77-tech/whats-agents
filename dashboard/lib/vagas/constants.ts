/**
 * Constantes para o módulo de Vagas
 */

import type { ShiftStatus } from './types'

/**
 * Cores de badge por status (estilo claro para cards)
 */
export const STATUS_BADGE_COLORS: Record<ShiftStatus, string> = {
  aberta: 'bg-green-100 text-green-800',
  reservada: 'bg-yellow-100 text-yellow-800',
  confirmada: 'bg-blue-100 text-blue-800',
  cancelada: 'bg-red-100 text-red-800',
  realizada: 'bg-gray-100 text-gray-800',
  fechada: 'bg-gray-100 text-gray-800',
}

/**
 * Cores de indicador por status (estilo sólido para calendário)
 */
export const STATUS_INDICATOR_COLORS: Record<ShiftStatus, string> = {
  aberta: 'bg-green-500',
  reservada: 'bg-yellow-500',
  confirmada: 'bg-blue-500',
  cancelada: 'bg-red-500',
  realizada: 'bg-gray-500',
  fechada: 'bg-gray-500',
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
