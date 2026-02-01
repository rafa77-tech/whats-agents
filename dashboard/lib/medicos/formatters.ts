/**
 * Funções de formatação para o módulo de Médicos
 */

import { STAGE_COLORS, STAGE_LABELS, EVENT_COLORS } from './constants'
import type { TimelineEventType } from './types'

/**
 * Gera as iniciais a partir do nome completo
 * @param nome - Nome completo do médico
 * @returns Iniciais em maiúsculas (max 2 caracteres)
 */
export function getInitials(nome: string | undefined | null): string {
  if (!nome) return 'XX'

  const parts = nome.trim().split(' ').filter(Boolean)
  if (parts.length === 0) return 'XX'

  const initials = parts
    .slice(0, 2)
    .map((part) => part[0] || '')
    .join('')
    .toUpperCase()

  return initials || 'XX'
}

/**
 * Retorna a cor do badge para um estágio da jornada
 * @param stage - Estágio da jornada
 * @returns String de classes CSS
 */
export function getStageColor(stage: string | undefined | null): string {
  if (!stage) return 'bg-gray-100 text-gray-800'
  return STAGE_COLORS[stage] || 'bg-gray-100 text-gray-800'
}

/**
 * Retorna o label traduzido para um estágio da jornada
 * @param stage - Estágio da jornada
 * @returns Label traduzido
 */
export function getStageLabel(stage: string | undefined | null): string {
  if (!stage) return 'Desconhecido'
  return STAGE_LABELS[stage] || stage
}

/**
 * Retorna a cor do ícone para um tipo de evento na timeline
 * @param eventType - Tipo do evento
 * @returns String de classes CSS
 */
export function getEventColor(eventType: string): string {
  return EVENT_COLORS[eventType as TimelineEventType] || 'bg-gray-100 text-gray-600'
}

/**
 * Formata o nome completo a partir de primeiro nome e sobrenome
 * @param primeiroNome - Primeiro nome
 * @param sobrenome - Sobrenome
 * @returns Nome completo formatado
 */
export function formatFullName(
  primeiroNome: string | undefined | null,
  sobrenome: string | undefined | null
): string {
  const parts = [primeiroNome, sobrenome].filter(Boolean)
  return parts.join(' ') || 'Sem nome'
}

/**
 * Formata localização (cidade + estado)
 * @param cidade - Nome da cidade
 * @param estado - Sigla do estado
 * @returns Localização formatada
 */
export function formatLocation(
  cidade: string | undefined | null,
  estado: string | undefined | null
): string {
  if (!cidade) return ''
  if (!estado) return cidade
  return `${cidade}, ${estado}`
}
