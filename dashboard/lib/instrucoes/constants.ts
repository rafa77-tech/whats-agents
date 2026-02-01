/**
 * Constantes para o modulo de Instrucoes (Diretrizes)
 */

import { Calendar, User, Building2, Briefcase, Globe, type LucideIcon } from 'lucide-react'
import type { Escopo, TipoDiretriz, SelectOption } from './types'

// =============================================================================
// Icones por escopo
// =============================================================================

/**
 * Mapeamento de escopo para icone Lucide
 */
export const ESCOPO_ICONS: Record<Escopo, LucideIcon> = {
  vaga: Calendar,
  medico: User,
  hospital: Building2,
  especialidade: Briefcase,
  global: Globe,
}

// =============================================================================
// Labels
// =============================================================================

/**
 * Labels para tipos de diretriz
 */
export const TIPO_LABELS: Record<TipoDiretriz, string> = {
  margem_negociacao: 'Margem de Negociacao',
  regra_especial: 'Regra Especial',
  info_adicional: 'Info Adicional',
}

/**
 * Labels para escopo
 */
export const ESCOPO_LABELS: Record<Escopo, string> = {
  vaga: 'Vaga',
  medico: 'Medico',
  hospital: 'Hospital',
  especialidade: 'Especialidade',
  global: 'Todas as conversas',
}

// =============================================================================
// Opcoes para selects
// =============================================================================

/**
 * Opcoes de tipo de diretriz
 */
export const TIPO_OPTIONS: SelectOption[] = [
  { value: 'margem_negociacao', label: 'Margem de Negociacao' },
  { value: 'regra_especial', label: 'Regra Especial' },
  { value: 'info_adicional', label: 'Informacao Adicional' },
]

/**
 * Opcoes de escopo
 */
export const ESCOPO_OPTIONS: SelectOption[] = [
  { value: 'global', label: 'Todas as conversas' },
  { value: 'hospital', label: 'Hospital especifico' },
  { value: 'especialidade', label: 'Especialidade' },
]

// =============================================================================
// Endpoints da API
// =============================================================================

/**
 * Endpoints da API de diretrizes
 */
export const API_ENDPOINTS = {
  diretrizes: '/api/diretrizes',
  hospitais: '/api/hospitais',
  especialidades: '/api/especialidades',
} as const

// =============================================================================
// Valores default
// =============================================================================

/**
 * Status default para busca de diretrizes ativas
 */
export const DEFAULT_STATUS_ATIVAS = 'ativa'

/**
 * Status para busca de historico
 */
export const DEFAULT_STATUS_HISTORICO = 'expirada,cancelada'

/**
 * Tipo default para nova diretriz
 */
export const DEFAULT_TIPO: TipoDiretriz = 'margem_negociacao'

/**
 * Escopo default para nova diretriz
 */
export const DEFAULT_ESCOPO: Escopo = 'global'
