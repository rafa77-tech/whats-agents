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
  novo: 'bg-status-neutral text-status-neutral-foreground',
  respondeu: 'bg-status-info text-status-info-foreground',
  negociando: 'bg-status-warning text-status-warning-foreground',
  convertido: 'bg-status-success text-status-success-foreground',
  perdido: 'bg-status-error text-status-error-foreground',
  // Inglês (aliases)
  prospecting: 'bg-status-neutral text-status-neutral-foreground',
  engaged: 'bg-status-info text-status-info-foreground',
  negotiating: 'bg-status-warning text-status-warning-foreground',
  converted: 'bg-status-success text-status-success-foreground',
  lost: 'bg-status-error text-status-error-foreground',
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
  message_sent: 'bg-status-info text-status-info-foreground',
  message_received: 'bg-status-success text-status-success-foreground',
  handoff: 'bg-status-warning text-status-warning-foreground',
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
