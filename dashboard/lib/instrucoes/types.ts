/**
 * Tipos para o modulo de Instrucoes (Diretrizes)
 */

import type { LucideIcon } from 'lucide-react'

// =============================================================================
// Enums / Union Types
// =============================================================================

/**
 * Tipos de diretriz disponiveis
 */
export type TipoDiretriz = 'margem_negociacao' | 'regra_especial' | 'info_adicional'

/**
 * Escopos de aplicacao da diretriz
 */
export type Escopo = 'vaga' | 'medico' | 'hospital' | 'especialidade' | 'global'

/**
 * Status da diretriz
 */
export type DiretrizStatus = 'ativa' | 'expirada' | 'cancelada'

// =============================================================================
// Interfaces de dados
// =============================================================================

/**
 * Conteudo da diretriz
 */
export interface DiretrizConteudo {
  valor_maximo?: number
  percentual_maximo?: number
  regra?: string
  info?: string
}

/**
 * Diretriz contextual
 */
export interface Diretriz {
  id: string
  tipo: TipoDiretriz
  escopo: Escopo
  vaga_id?: string | undefined
  cliente_id?: string | undefined
  hospital_id?: string | undefined
  especialidade_id?: string | undefined
  conteudo: DiretrizConteudo
  criado_por: string
  criado_em: string
  expira_em?: string | undefined
  status: DiretrizStatus
  vagas?: { data: string; hospital_id: string } | null
  clientes?: { primeiro_nome: string; sobrenome: string; telefone: string } | null
  hospitais?: { nome: string } | null
  especialidades?: { nome: string } | null
}

/**
 * Hospital para seletor
 */
export interface Hospital {
  id: string
  nome: string
}

/**
 * Especialidade para seletor
 */
export interface Especialidade {
  id: string
  nome: string
}

// =============================================================================
// Interfaces de filtros
// =============================================================================

/**
 * Filtros de busca de diretrizes
 */
export interface DiretrizFilters {
  status?: string | undefined
}

// =============================================================================
// Interfaces de props de componentes
// =============================================================================

/**
 * Props do componente NovaInstrucaoDialog
 */
export interface NovaInstrucaoDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}

/**
 * Props do componente DiretrizesTable
 */
export interface DiretrizesTableProps {
  diretrizes: Diretriz[]
  loading: boolean
  onCancelar: (d: Diretriz) => void
  showActions: boolean
}

// =============================================================================
// Interfaces de payload
// =============================================================================

/**
 * Payload para criar diretriz
 */
export interface CriarDiretrizPayload {
  tipo: TipoDiretriz
  escopo: Escopo
  conteudo: DiretrizConteudo
  hospital_id?: string
  especialidade_id?: string
  expira_em?: string
}

/**
 * Payload para cancelar diretriz
 */
export interface CancelarDiretrizPayload {
  status: 'cancelada'
}

// =============================================================================
// Interfaces de retorno de hooks
// =============================================================================

/**
 * Retorno do hook useInstrucoes
 */
export interface UseInstrucoesReturn {
  diretrizes: Diretriz[]
  loading: boolean
  error: string | null
  tab: 'ativas' | 'historico'
  actions: {
    setTab: (tab: 'ativas' | 'historico') => void
    refresh: () => Promise<void>
    cancelar: (diretriz: Diretriz) => Promise<void>
  }
}

/**
 * Retorno do hook useNovaInstrucao
 */
export interface UseNovaInstrucaoReturn {
  loading: boolean
  hospitais: Hospital[]
  especialidades: Especialidade[]
  loadingListas: boolean
  criar: (payload: CriarDiretrizPayload) => Promise<boolean>
}

// =============================================================================
// Tipos auxiliares
// =============================================================================

/**
 * Mapeamento de escopo para icone
 */
export type EscopoIconMap = Record<Escopo, LucideIcon>

/**
 * Mapeamento de tipo para label
 */
export type TipoLabelMap = Record<TipoDiretriz, string>

/**
 * Opcao para select
 */
export interface SelectOption {
  value: string
  label: string
}
