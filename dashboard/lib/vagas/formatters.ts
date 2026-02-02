/**
 * Funções de formatação para o módulo de Vagas
 */

import type { ShiftStatus } from './types'
import { STATUS_BADGE_COLORS, STATUS_INDICATOR_COLORS, STATUS_LABELS } from './constants'

/**
 * Formata valor em BRL
 * @param value - Valor numérico
 * @returns String formatada (ex: "R$ 1.500,00")
 */
export function formatCurrency(value: number): string {
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(value)
}

/**
 * Parse de data da vaga para objeto Date
 * Adiciona T00:00:00 para evitar problemas de timezone
 * @param dateString - Data no formato YYYY-MM-DD
 * @returns Date object
 */
export function parseShiftDate(dateString: string): Date {
  return new Date(dateString + 'T00:00:00')
}

/**
 * Retorna a cor do badge para um status
 * @param status - Status da vaga
 * @returns String de classes CSS
 */
export function getStatusBadgeColor(status: string): string {
  return (
    STATUS_BADGE_COLORS[status as ShiftStatus] || 'bg-status-neutral text-status-neutral-foreground'
  )
}

/**
 * Retorna a cor do indicador para um status
 * @param status - Status da vaga
 * @returns String de classes CSS
 */
export function getStatusIndicatorColor(status: string): string {
  return STATUS_INDICATOR_COLORS[status as ShiftStatus] || 'bg-status-neutral-solid'
}

/**
 * Retorna o label traduzido para um status
 * @param status - Status da vaga
 * @returns Label traduzido
 */
export function getStatusLabel(status: string): string {
  return STATUS_LABELS[status as ShiftStatus] || status
}

/**
 * Formata horário de início e fim
 * @param horaInicio - Hora de início (HH:MM)
 * @param horaFim - Hora de fim (HH:MM)
 * @returns String formatada (ex: "08:00 - 18:00")
 */
export function formatTimeRange(horaInicio: string, horaFim: string): string {
  return `${horaInicio} - ${horaFim}`
}

/**
 * Formata contagem de reservas
 * @param count - Número de reservas
 * @returns String formatada (ex: "1 reserva" ou "3 reservas")
 */
export function formatReservasCount(count: number): string {
  if (count === 0) return ''
  return count === 1 ? '1 reserva' : `${count} reservas`
}
