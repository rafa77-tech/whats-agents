/**
 * Tipos centralizados para o módulo de Vagas
 */

/**
 * Status possíveis de uma vaga
 */
export type ShiftStatus =
  | 'aberta'
  | 'reservada'
  | 'confirmada'
  | 'cancelada'
  | 'realizada'
  | 'fechada'

/**
 * Nível de criticidade/urgência de uma vaga
 */
export type Criticidade = 'normal' | 'urgente' | 'critica'

/**
 * Vaga resumida (usada em listagens)
 */
export interface Shift {
  id: string
  hospital: string
  hospital_id: string
  especialidade: string
  especialidade_id: string
  data: string // YYYY-MM-DD
  hora_inicio: string // HH:MM
  hora_fim: string // HH:MM
  valor: number
  status: ShiftStatus | string
  criticidade: string
  reservas_count: number
  created_at: string
  contato_nome: string | null
  contato_whatsapp: string | null
}

/**
 * Vaga detalhada (usada em página de detalhes)
 */
export interface ShiftDetail extends Omit<Shift, 'reservas_count'> {
  setor: string | null
  setor_id: string | null
  cliente_id: string | null
  cliente_nome: string | null
  updated_at: string | null
  contato_nome: string | null
  contato_whatsapp: string | null
}

/**
 * Médico (usado para atribuição de vagas)
 */
export interface Doctor {
  id: string
  nome: string
  telefone: string
  especialidade?: string
}

/**
 * Filtros para busca de vagas
 */
export interface ShiftFilters {
  status?: string | undefined
  criticidade?: string | undefined
  hospital_id?: string | undefined
  especialidade_id?: string | undefined
  date_from?: string | undefined
  date_to?: string | undefined
}

/**
 * Resposta paginada da API de vagas
 */
export interface ShiftListResponse {
  data: Shift[]
  total: number
  pages: number
}

/**
 * Modo de visualização
 */
export type ViewMode = 'list' | 'calendar'

/**
 * Opção genérica para selects (hospitais, especialidades)
 */
export interface SelectOption {
  id: string
  nome: string
}
