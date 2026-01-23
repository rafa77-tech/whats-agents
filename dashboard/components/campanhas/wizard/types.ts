/**
 * Wizard Types and Constants - Sprint 34 E03
 */

import { Settings, Users, MessageSquare, CheckCircle2 } from 'lucide-react'

export type TipoCampanha = 'oferta_plantao' | 'reativacao' | 'followup' | 'descoberta'
export type Categoria = 'marketing' | 'operacional' | 'relacionamento'
export type Tom = 'amigavel' | 'profissional' | 'urgente' | 'casual'
export type AudienciaTipo = 'todos' | 'filtrado'

export interface CampanhaFormData {
  // Step 1 - Configuracao
  nome_template: string
  tipo_campanha: TipoCampanha
  categoria: Categoria
  objetivo: string

  // Step 2 - Audiencia
  audiencia_tipo: AudienciaTipo
  especialidades: string[]
  regioes: string[]
  status_cliente: string[]

  // Step 3 - Mensagem
  corpo: string
  tom: Tom

  // Step 4 - Agendamento
  agendar: boolean
  agendar_para: string
}

export const INITIAL_FORM_DATA: CampanhaFormData = {
  nome_template: '',
  tipo_campanha: 'oferta_plantao',
  categoria: 'marketing',
  objetivo: '',
  audiencia_tipo: 'todos',
  especialidades: [],
  regioes: [],
  status_cliente: [],
  corpo: '',
  tom: 'amigavel',
  agendar: false,
  agendar_para: '',
}

export interface WizardStep {
  id: number
  title: string
  icon: typeof Settings
}

export const WIZARD_STEPS: WizardStep[] = [
  { id: 1, title: 'Configuracao', icon: Settings },
  { id: 2, title: 'Audiencia', icon: Users },
  { id: 3, title: 'Mensagem', icon: MessageSquare },
  { id: 4, title: 'Revisao', icon: CheckCircle2 },
]

export const TIPOS_CAMPANHA = [
  { value: 'oferta_plantao', label: 'Oferta de Plantao' },
  { value: 'reativacao', label: 'Reativacao' },
  { value: 'followup', label: 'Follow-up' },
  { value: 'descoberta', label: 'Descoberta' },
] as const

export const CATEGORIAS = [
  { value: 'marketing', label: 'Marketing' },
  { value: 'operacional', label: 'Operacional' },
  { value: 'relacionamento', label: 'Relacionamento' },
] as const

export const TONS = [
  { value: 'amigavel', label: 'Amigavel' },
  { value: 'profissional', label: 'Profissional' },
  { value: 'urgente', label: 'Urgente' },
  { value: 'casual', label: 'Casual' },
] as const

// ESPECIALIDADES e REGIOES agora sao buscados dinamicamente via /api/filtros
