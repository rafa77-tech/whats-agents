/**
 * Tipos centralizados para o módulo de Médicos
 */

/**
 * Estágios da jornada do médico no funil
 */
export type JourneyStage =
  | 'novo'
  | 'prospecting'
  | 'respondeu'
  | 'engaged'
  | 'negociando'
  | 'negotiating'
  | 'convertido'
  | 'converted'
  | 'perdido'
  | 'lost'

/**
 * Tipos de evento na timeline
 */
export type TimelineEventType = 'message_sent' | 'message_received' | 'handoff'

/**
 * Médico resumido (usado em listagens)
 */
export interface Doctor {
  id: string
  nome: string
  telefone: string
  especialidade?: string
  cidade?: string
  stage_jornada?: string
  opt_out: boolean
  created_at: string
  app_enviado?: boolean // Links do app foram enviados
  app_enviado_em?: string // Data/hora do envio
}

/**
 * Médico detalhado (usado na página de perfil)
 */
export interface DoctorDetail extends Doctor {
  crm?: string
  estado?: string
  email?: string
  opt_out_data?: string
  pressure_score_atual?: number
  contexto_consolidado?: string
  conversations_count: number
  last_interaction_at?: string
}

/**
 * Médico para stats (versão reduzida usada em DoctorStats)
 */
export interface DoctorStats {
  id: string
  nome: string
  stage_jornada?: string
  pressure_score_atual?: number
  contexto_consolidado?: string
  conversations_count: number
  last_interaction_at?: string
  created_at: string
}

/**
 * Médico para actions (versão reduzida usada em DoctorActions)
 */
export interface DoctorActions {
  id: string
  nome: string
  stage_jornada?: string
  opt_out: boolean
}

/**
 * Evento da timeline de interações
 */
export interface TimelineEvent {
  id: string
  type: string
  title: string
  description?: string
  created_at: string
  metadata?: Record<string, unknown>
}

/**
 * Filtros para busca de médicos
 */
export interface DoctorFilters {
  stage_jornada?: string | undefined
  especialidade?: string | undefined
  opt_out?: boolean | undefined
  search?: string | undefined
}

/**
 * Resposta paginada da API de médicos
 */
export interface DoctorListResponse {
  data: Doctor[]
  total: number
  pages: number
}

/**
 * Opção genérica para selects
 */
export interface SelectOption {
  value: string
  label: string
}
