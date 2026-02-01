/**
 * Funções de formatação para o módulo de Group Entry
 */

import type { LinkStatus, QueueItemStatus, GroupEntryConfig, GroupEntryConfigUI } from './types'
import {
  LINK_STATUS_LABELS,
  LINK_STATUS_BADGE_COLORS,
  QUEUE_STATUS_LABELS,
  QUEUE_STATUS_BADGE_COLORS,
  WHATSAPP_LINK_PREFIX,
  CAPACITY_WARNING_THRESHOLD,
  CAPACITY_DANGER_THRESHOLD,
} from './constants'

/**
 * Retorna o label traduzido para um status de link
 */
export function getLinkStatusLabel(status: string): string {
  return LINK_STATUS_LABELS[status as LinkStatus] || status
}

/**
 * Retorna a cor do badge para um status de link
 */
export function getLinkStatusBadgeColor(status: string): string {
  return LINK_STATUS_BADGE_COLORS[status as LinkStatus] || 'bg-gray-100 text-gray-800'
}

/**
 * Retorna o label traduzido para um status da fila
 */
export function getQueueStatusLabel(status: string): string {
  return QUEUE_STATUS_LABELS[status as QueueItemStatus] || status
}

/**
 * Retorna a cor do badge para um status da fila
 */
export function getQueueStatusBadgeColor(status: string): string {
  return QUEUE_STATUS_BADGE_COLORS[status as QueueItemStatus] || 'bg-gray-100 text-gray-800'
}

/**
 * Formata URL do link de grupo para exibição (trunca prefixo)
 */
export function formatLinkUrl(url: string): string {
  return url.replace(WHATSAPP_LINK_PREFIX, '...')
}

/**
 * Formata data para exibição no formato brasileiro
 */
export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('pt-BR')
}

/**
 * Formata horário para exibição
 */
export function formatTime(dateString: string): string {
  return new Date(dateString).toLocaleTimeString('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Calcula porcentagem de capacidade
 */
export function calculateCapacityPercentage(used: number, total: number): number {
  if (total <= 0) return 0
  return Math.round((used / total) * 100)
}

/**
 * Retorna a cor da barra de capacidade baseada na porcentagem
 */
export function getCapacityColor(percentage: number): string {
  if (percentage >= CAPACITY_DANGER_THRESHOLD) return 'bg-red-500'
  if (percentage >= CAPACITY_WARNING_THRESHOLD) return 'bg-yellow-500'
  return 'bg-green-500'
}

/**
 * Verifica se a capacidade está em warning
 */
export function isCapacityWarning(percentage: number): boolean {
  return percentage >= CAPACITY_WARNING_THRESHOLD
}

/**
 * Converte configuração da API para formato da UI (snake_case -> camelCase)
 */
export function configApiToUI(config: Partial<GroupEntryConfig>): GroupEntryConfigUI {
  return {
    gruposPorDia: config.grupos_por_dia ?? 10,
    intervaloMin: config.intervalo_min ?? 30,
    intervaloMax: config.intervalo_max ?? 60,
    horarioInicio: config.horario_inicio ?? '08:00',
    horarioFim: config.horario_fim ?? '20:00',
    diasAtivos: config.dias_ativos ?? ['seg', 'ter', 'qua', 'qui', 'sex'],
    autoValidar: config.auto_validar ?? true,
    autoAgendar: config.auto_agendar ?? false,
    notificarFalhas: config.notificar_falhas ?? true,
  }
}

/**
 * Converte configuração da UI para formato da API (camelCase -> snake_case)
 */
export function configUIToApi(config: GroupEntryConfigUI): GroupEntryConfig {
  return {
    grupos_por_dia: config.gruposPorDia,
    intervalo_min: config.intervaloMin,
    intervalo_max: config.intervaloMax,
    horario_inicio: config.horarioInicio,
    horario_fim: config.horarioFim,
    dias_ativos: config.diasAtivos,
    auto_validar: config.autoValidar,
    auto_agendar: config.autoAgendar,
    notificar_falhas: config.notificarFalhas,
  }
}

/**
 * Valida configuração
 */
export function validateConfig(config: GroupEntryConfigUI): string[] {
  const errors: string[] = []

  if (config.intervaloMin >= config.intervaloMax) {
    errors.push('Intervalo mínimo deve ser menor que o máximo')
  }

  if (config.horarioInicio >= config.horarioFim) {
    errors.push('Horário de início deve ser anterior ao fim')
  }

  if (config.diasAtivos.length === 0) {
    errors.push('Selecione pelo menos um dia da semana')
  }

  if (config.gruposPorDia < 1 || config.gruposPorDia > 20) {
    errors.push('Grupos por dia deve estar entre 1 e 20')
  }

  return errors
}

/**
 * Verifica se um arquivo tem extensão válida para importação
 */
export function isValidFileExtension(filename: string): boolean {
  const lowerFilename = filename.toLowerCase()
  return lowerFilename.endsWith('.csv') || lowerFilename.endsWith('.xlsx')
}
