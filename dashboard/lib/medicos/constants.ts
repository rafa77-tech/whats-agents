/**
 * Constantes para o módulo de Médicos
 */

import type { JourneyStage, TimelineEventType } from './types'

/**
 * Cores de badge por estágio da jornada
 * Inclui versões em português e inglês para compatibilidade
 */
export const STAGE_COLORS: Record<string, string> = {
  // Português
  novo: 'bg-gray-100 text-gray-800',
  respondeu: 'bg-blue-100 text-blue-800',
  negociando: 'bg-yellow-100 text-yellow-800',
  convertido: 'bg-green-100 text-green-800',
  perdido: 'bg-red-100 text-red-800',
  // Inglês (aliases)
  prospecting: 'bg-gray-100 text-gray-800',
  engaged: 'bg-blue-100 text-blue-800',
  negotiating: 'bg-yellow-100 text-yellow-800',
  converted: 'bg-green-100 text-green-800',
  lost: 'bg-red-100 text-red-800',
}

/**
 * Labels traduzidos por estágio da jornada
 * Inclui versões em português e inglês para compatibilidade
 */
export const STAGE_LABELS: Record<string, string> = {
  // Português
  novo: 'Novo',
  respondeu: 'Respondeu',
  negociando: 'Negociando',
  convertido: 'Convertido',
  perdido: 'Perdido',
  // Inglês (aliases)
  prospecting: 'Prospecção',
  engaged: 'Engajado',
  negotiating: 'Negociando',
  converted: 'Convertido',
  lost: 'Perdido',
}

/**
 * Opções de estágio para filtros e selects
 */
export const STAGE_OPTIONS = [
  { value: 'novo', label: 'Novo' },
  { value: 'respondeu', label: 'Respondeu' },
  { value: 'negociando', label: 'Negociando' },
  { value: 'convertido', label: 'Convertido' },
  { value: 'perdido', label: 'Perdido' },
] as const

/**
 * Opções de especialidade para filtros
 */
export const ESPECIALIDADE_OPTIONS = [
  { value: 'Cardiologia', label: 'Cardiologia' },
  { value: 'Clinica Medica', label: 'Clínica Médica' },
  { value: 'Ortopedia', label: 'Ortopedia' },
  { value: 'Pediatria', label: 'Pediatria' },
  { value: 'Cirurgia Geral', label: 'Cirurgia Geral' },
  { value: 'Anestesiologia', label: 'Anestesiologia' },
] as const

/**
 * Cores de ícone por tipo de evento na timeline
 */
export const EVENT_COLORS: Record<TimelineEventType, string> = {
  message_sent: 'bg-blue-100 text-blue-600',
  message_received: 'bg-green-100 text-green-600',
  handoff: 'bg-orange-100 text-orange-600',
}

/**
 * Lista de todos os estágios da jornada (português)
 */
export const ALL_STAGES: JourneyStage[] = [
  'novo',
  'respondeu',
  'negociando',
  'convertido',
  'perdido',
]

/**
 * Configurações de paginação
 */
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
} as const

/**
 * Configuração do debounce de busca (em ms)
 */
export const SEARCH_DEBOUNCE_MS = 300
