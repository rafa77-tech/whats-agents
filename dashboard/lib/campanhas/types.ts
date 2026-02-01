/**
 * Tipos centralizados para o módulo Campanhas
 * Sprint 43: UX & Operação Unificada
 */

// ============================================
// Tipos de Cliente
// ============================================

export interface Cliente {
  id: string
  primeiro_nome: string
  sobrenome?: string
  telefone: string
  especialidade?: string
}

export interface AudienciaCliente extends Cliente {
  cidade?: string
  estado?: string
}

export interface ClienteBusca extends AudienciaCliente {
  na_campanha: boolean
}

// ============================================
// Tipos de Envio
// ============================================

export type EnvioStatus = 'pendente' | 'enviado' | 'entregue' | 'visualizado' | 'falhou'

export interface Envio {
  id: number
  cliente_id: string
  status: EnvioStatus
  conteudo_enviado: string
  created_at: string
  enviado_em?: string
  entregue_em?: string
  visualizado_em?: string
  falhou_em?: string
  clientes: Cliente | null
}

export interface EnvioStatusConfig {
  label: string
  color: string
  icon: string
}

export const ENVIO_STATUS_CONFIG: Record<EnvioStatus, EnvioStatusConfig> = {
  pendente: { label: 'Pendente', color: 'text-gray-500', icon: 'Clock' },
  enviado: { label: 'Enviado', color: 'text-blue-500', icon: 'Send' },
  entregue: { label: 'Entregue', color: 'text-green-500', icon: 'CheckCircle2' },
  visualizado: { label: 'Visualizado', color: 'text-purple-500', icon: 'Eye' },
  falhou: { label: 'Falhou', color: 'text-red-500', icon: 'XCircle' },
}

// ============================================
// Tipos de Metricas
// ============================================

export interface MetricasCampanha {
  total: number
  enviados: number
  entregues: number
  visualizados: number
  falhas: number
  taxa_entrega: number
  taxa_visualizacao: number
}

// ============================================
// Tipos de Campanha
// ============================================

export type CampanhaStatus =
  | 'rascunho'
  | 'agendada'
  | 'ativa'
  | 'concluida'
  | 'pausada'
  | 'cancelada'

export type TipoCampanha = 'oferta_plantao' | 'reativacao' | 'followup' | 'descoberta'

export interface Campanha {
  id: number
  nome_template: string
  tipo_campanha: TipoCampanha
  categoria: string
  status: CampanhaStatus
  objetivo?: string
  corpo: string
  tom?: string
  agendar_para?: string
  iniciada_em?: string
  concluida_em?: string
  created_at: string
  created_by?: string
  audience_filters?: Record<string, unknown>
  envios: Envio[]
  metricas: MetricasCampanha
}

export interface CampanhaStatusConfig {
  label: string
  color: string
  icon: string
}

export const CAMPANHA_STATUS_CONFIG: Record<CampanhaStatus, CampanhaStatusConfig> = {
  rascunho: {
    label: 'Rascunho',
    color: 'bg-gray-100 text-gray-800 border-gray-200',
    icon: 'FileEdit',
  },
  agendada: {
    label: 'Agendada',
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    icon: 'Clock',
  },
  ativa: {
    label: 'Ativa',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    icon: 'Play',
  },
  concluida: {
    label: 'Concluida',
    color: 'bg-green-100 text-green-800 border-green-200',
    icon: 'CheckCircle2',
  },
  pausada: {
    label: 'Pausada',
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    icon: 'Pause',
  },
  cancelada: {
    label: 'Cancelada',
    color: 'bg-red-100 text-red-800 border-red-200',
    icon: 'XCircle',
  },
}

export const TIPO_CAMPANHA_LABELS: Record<TipoCampanha, string> = {
  oferta_plantao: 'Oferta de Plantao',
  reativacao: 'Reativacao',
  followup: 'Follow-up',
  descoberta: 'Descoberta',
}

// ============================================
// Tipos de Audiencia
// ============================================

export interface ExemploMensagem {
  destinatario: string
  mensagem: string
}

export interface Audiencia {
  total: number
  filters: Record<string, unknown>
  clientes: AudienciaCliente[]
  exemplos_mensagens: ExemploMensagem[]
  variacoes_possiveis: number
  modo: 'manual' | 'filtros'
}

// ============================================
// Tipos de Request/Response
// ============================================

export interface ListarCampanhasParams {
  status?: CampanhaStatus
  tipo?: TipoCampanha
}

export interface CriarCampanhaRequest {
  nome_template: string
  tipo_campanha: TipoCampanha
  categoria: string
  corpo: string
  objetivo?: string
  tom?: string
  agendar_para?: string
  audience_filters?: Record<string, unknown>
}

export interface AtualizarCampanhaRequest {
  status?: CampanhaStatus
}

export interface AtualizarAudienciaRequest {
  cliente_ids?: string[]
  excluded_cliente_ids?: string[]
  filters?: Record<string, unknown>
}

// ============================================
// Tipos de Dialogs/UI State
// ============================================

export type CampanhaAction = 'iniciar' | 'pausar' | 'retomar' | 'cancelar'

export interface ConfirmDialogState {
  action: CampanhaAction
  title: string
  description: string
}
