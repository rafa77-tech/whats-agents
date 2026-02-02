/**
 * Constantes para o modulo de Qualidade
 */

import type { SuggestionType, SuggestionStatus, MetricCardColor } from './types'

// =============================================================================
// Limites e configuracoes
// =============================================================================

/**
 * Limite de conversas por fetch
 */
export const CONVERSATIONS_FETCH_LIMIT = 20

/**
 * Numero maximo de estrelas para avaliacao
 */
export const MAX_RATING_STARS = 5

/**
 * Numero maximo de padroes violados exibidos
 */
export const MAX_PATTERNS_DISPLAYED = 5

// =============================================================================
// Opcoes de tipo de sugestao
// =============================================================================

/**
 * Tipos de sugestao disponiveis
 */
export const SUGGESTION_TYPES: Array<{ value: SuggestionType; label: string }> = [
  { value: 'tom', label: 'Tom de voz' },
  { value: 'resposta', label: 'Tipo de resposta' },
  { value: 'abertura', label: 'Mensagem de abertura' },
  { value: 'objecao', label: 'Tratamento de objecao' },
]

// =============================================================================
// Cores e estilos
// =============================================================================

/**
 * Classes de cor para metric cards
 */
export const METRIC_CARD_COLORS: Record<
  MetricCardColor,
  { bg: string; text: string; icon: string }
> = {
  green: {
    bg: 'bg-status-success/20',
    text: 'text-status-success-foreground',
    icon: 'text-status-success-foreground/70',
  },
  yellow: {
    bg: 'bg-status-warning/20',
    text: 'text-status-warning-foreground',
    icon: 'text-status-warning-foreground/70',
  },
  blue: {
    bg: 'bg-status-info/20',
    text: 'text-status-info-foreground',
    icon: 'text-status-info-foreground/70',
  },
  red: {
    bg: 'bg-status-error/20',
    text: 'text-status-error-foreground',
    icon: 'text-status-error-foreground/70',
  },
}

/**
 * Classes de cor para badges de status de sugestao
 */
export const SUGGESTION_STATUS_COLORS: Record<SuggestionStatus, string> = {
  pending: 'bg-status-warning text-status-warning-foreground',
  approved: 'bg-status-info text-status-info-foreground',
  rejected: 'bg-status-error text-status-error-foreground',
  implemented: 'bg-status-success text-status-success-foreground',
}

/**
 * Labels de status de sugestao em portugues
 */
export const SUGGESTION_STATUS_LABELS: Record<SuggestionStatus, string> = {
  pending: 'Pendente',
  approved: 'Aprovada',
  rejected: 'Rejeitada',
  implemented: 'Implementada',
}

/**
 * Classes de cor para badges de tipo de sugestao
 */
export const SUGGESTION_TYPE_COLORS: Record<SuggestionType, string> = {
  tom: 'bg-accent/20 text-accent',
  resposta: 'bg-status-info text-status-info-foreground',
  abertura: 'bg-status-success text-status-success-foreground',
  objecao: 'bg-trust-laranja text-trust-laranja-foreground',
}

// =============================================================================
// Valores default
// =============================================================================

/**
 * Metricas default quando API falha
 */
export const DEFAULT_METRICS = {
  avaliadas: 0,
  pendentes: 0,
  scoreMedio: 0,
  validacaoTaxa: 98,
  validacaoFalhas: 0,
  padroesViolados: [],
}

/**
 * Ratings default para avaliacao
 */
export const DEFAULT_RATINGS = {
  naturalidade: 0,
  persona: 0,
  objetivo: 0,
  satisfacao: 0,
}

// =============================================================================
// Endpoints da API
// =============================================================================

/**
 * Endpoints utilizados pelo modulo de qualidade
 */
export const API_ENDPOINTS = {
  metricsPerformance: '/api/admin/metricas/performance',
  metricsValidation: '/api/admin/validacao/metricas',
  conversations: '/api/admin/conversas',
  conversationDetail: (id: string) => `/api/admin/conversas/${id}`,
  evaluations: '/api/admin/avaliacoes',
  suggestions: '/api/admin/sugestoes',
  suggestionDetail: (id: string) => `/api/admin/sugestoes/${id}`,
}

// =============================================================================
// Opcoes de filtro
// =============================================================================

/**
 * Opcoes de filtro de conversas avaliadas
 */
export const CONVERSATION_FILTER_OPTIONS = [
  { value: 'all', label: 'Todas' },
  { value: 'false', label: 'Nao Avaliadas' },
  { value: 'true', label: 'Avaliadas' },
]

/**
 * Opcoes de filtro de status de sugestao
 */
export const SUGGESTION_STATUS_FILTER_OPTIONS = [
  { value: 'all', label: 'Todas' },
  { value: 'pending', label: 'Pendentes' },
  { value: 'approved', label: 'Aprovadas' },
  { value: 'rejected', label: 'Rejeitadas' },
  { value: 'implemented', label: 'Implementadas' },
]

/**
 * Criterios de avaliacao
 */
export const EVALUATION_CRITERIA = [
  { key: 'naturalidade', label: 'Naturalidade' },
  { key: 'persona', label: 'Persona' },
  { key: 'objetivo', label: 'Objetivo' },
  { key: 'satisfacao', label: 'Satisfacao' },
] as const
