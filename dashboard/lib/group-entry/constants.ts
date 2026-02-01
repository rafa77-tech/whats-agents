/**
 * Constantes para o módulo de Group Entry
 */

import type { LinkStatus, QueueItemStatus, DiaSemana, GroupEntryConfigUI } from './types'

/**
 * Labels de status de links
 */
export const LINK_STATUS_LABELS: Record<LinkStatus, string> = {
  pending: 'Pendente',
  validated: 'Validado',
  scheduled: 'Agendado',
  processed: 'Processado',
  failed: 'Falhou',
}

/**
 * Cores de badge para status de links
 */
export const LINK_STATUS_BADGE_COLORS: Record<LinkStatus, string> = {
  pending: 'bg-gray-100 text-gray-800',
  validated: 'bg-blue-100 text-blue-800',
  scheduled: 'bg-yellow-100 text-yellow-800',
  processed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

/**
 * Labels de status da fila
 */
export const QUEUE_STATUS_LABELS: Record<QueueItemStatus, string> = {
  queued: 'Na Fila',
  processing: 'Processando',
}

/**
 * Cores de badge para status da fila
 */
export const QUEUE_STATUS_BADGE_COLORS: Record<QueueItemStatus, string> = {
  queued: 'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
}

/**
 * Dias da semana
 */
export const DIAS_SEMANA: DiaSemana[] = [
  { key: 'seg', label: 'Seg' },
  { key: 'ter', label: 'Ter' },
  { key: 'qua', label: 'Qua' },
  { key: 'qui', label: 'Qui' },
  { key: 'sex', label: 'Sex' },
  { key: 'sab', label: 'Sab' },
  { key: 'dom', label: 'Dom' },
]

/**
 * Configuração padrão
 */
export const DEFAULT_CONFIG: GroupEntryConfigUI = {
  gruposPorDia: 10,
  intervaloMin: 30,
  intervaloMax: 60,
  horarioInicio: '08:00',
  horarioFim: '20:00',
  diasAtivos: ['seg', 'ter', 'qua', 'qui', 'sex'],
  autoValidar: true,
  autoAgendar: false,
  notificarFalhas: true,
}

/**
 * Limites de configuração
 */
export const CONFIG_LIMITS = {
  gruposPorDia: { min: 1, max: 20 },
  intervaloMin: { min: 15, max: 120 },
  intervaloMax: { min: 30, max: 180 },
} as const

/**
 * Intervalo de auto-refresh da fila (em ms)
 */
export const QUEUE_REFRESH_INTERVAL = 30000

/**
 * Limite padrão de links por página
 */
export const DEFAULT_LINKS_LIMIT = 20

/**
 * Prefixo de URL do WhatsApp
 */
export const WHATSAPP_LINK_PREFIX = 'https://chat.whatsapp.com/'

/**
 * Extensões de arquivo aceitas para importação
 */
export const ACCEPTED_FILE_EXTENSIONS = ['.csv', '.xlsx']

/**
 * Threshold de capacidade para warning
 */
export const CAPACITY_WARNING_THRESHOLD = 80

/**
 * Threshold de capacidade para danger
 */
export const CAPACITY_DANGER_THRESHOLD = 90
