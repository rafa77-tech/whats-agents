/**
 * Funcoes de formatacao e parsing para o modulo de Qualidade
 */

import type {
  QualityMetrics,
  Conversation,
  ConversationDetail,
  Suggestion,
  Message,
  PerformanceMetricsResponse,
  ValidationMetricsResponse,
  ConversationsResponse,
  ConversationDetailResponse,
  SuggestionsResponse,
  SuggestionStatus,
  SuggestionType,
} from './types'
import { DEFAULT_METRICS } from './constants'

// =============================================================================
// Parsers de resposta da API
// =============================================================================

/**
 * Parse da resposta de metricas de performance e validacao
 */
export function parseMetricsResponse(
  performanceData: PerformanceMetricsResponse | null,
  validacaoData: ValidationMetricsResponse | null
): QualityMetrics {
  return {
    avaliadas: performanceData?.avaliadas ?? DEFAULT_METRICS.avaliadas,
    pendentes: performanceData?.pendentes ?? DEFAULT_METRICS.pendentes,
    scoreMedio: performanceData?.score_medio ?? DEFAULT_METRICS.scoreMedio,
    validacaoTaxa: validacaoData?.taxa_sucesso ?? DEFAULT_METRICS.validacaoTaxa,
    validacaoFalhas: validacaoData?.falhas ?? DEFAULT_METRICS.validacaoFalhas,
    padroesViolados: validacaoData?.padroes_violados ?? DEFAULT_METRICS.padroesViolados,
  }
}

/**
 * Parse da resposta de lista de conversas
 */
export function parseConversationsResponse(data: ConversationsResponse): Conversation[] {
  if (!data.conversas) return []

  return data.conversas.map((c) => ({
    id: c.id,
    medicoNome: c.medico_nome ?? 'Desconhecido',
    mensagens: c.total_mensagens ?? 0,
    status: c.status,
    avaliada: c.avaliada,
    criadaEm: c.criada_em,
  }))
}

/**
 * Parse da resposta de detalhes de conversa
 */
export function parseConversationDetailResponse(
  data: ConversationDetailResponse
): ConversationDetail {
  return {
    id: data.id,
    medicoNome: data.medico_nome ?? 'Desconhecido',
    mensagens: parseMessagesResponse(data.interacoes ?? []),
  }
}

/**
 * Parse da lista de mensagens
 */
export function parseMessagesResponse(
  interacoes: ConversationDetailResponse['interacoes']
): Message[] {
  if (!interacoes) return []

  return interacoes.map((m) => ({
    id: m.id,
    remetente: m.remetente,
    conteudo: m.conteudo,
    criadaEm: m.criada_em,
  }))
}

/**
 * Parse da resposta de sugestoes
 */
export function parseSuggestionsResponse(data: SuggestionsResponse): Suggestion[] {
  if (!data.sugestoes) return []

  return data.sugestoes.map((s) => {
    const suggestion: Suggestion = {
      id: s.id,
      tipo: s.tipo as SuggestionType,
      descricao: s.descricao,
      status: s.status as SuggestionStatus,
      criadaEm: s.criada_em,
    }
    if (s.exemplos) {
      suggestion.exemplos = s.exemplos
    }
    return suggestion
  })
}

// =============================================================================
// Formatadores de data
// =============================================================================

/**
 * Formata data para exibicao em formato brasileiro (DD/MM/YYYY)
 */
export function formatDateBR(dateString: string): string {
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) {
      return dateString
    }
    return date.toLocaleDateString('pt-BR')
  } catch {
    return dateString
  }
}

/**
 * Formata hora para exibicao (HH:MM)
 */
export function formatTimeBR(dateString: string): string {
  try {
    const date = new Date(dateString)
    if (isNaN(date.getTime())) {
      return ''
    }
    return date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return ''
  }
}

/**
 * Formata data e hora para exibicao
 */
export function formatDateTimeBR(dateString: string): string {
  try {
    return new Date(dateString).toLocaleString('pt-BR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return dateString
  }
}

// =============================================================================
// Formatadores de ID
// =============================================================================

/**
 * Trunca ID para exibicao (primeiros 8 caracteres)
 */
export function formatShortId(id: string): string {
  return `#${id.slice(0, 8)}`
}

// =============================================================================
// Validadores
// =============================================================================

/**
 * Verifica se todas as avaliacoes foram preenchidas
 */
export function isRatingsComplete(ratings: {
  naturalidade: number
  persona: number
  objetivo: number
  satisfacao: number
}): boolean {
  return (
    ratings.naturalidade > 0 &&
    ratings.persona > 0 &&
    ratings.objetivo > 0 &&
    ratings.satisfacao > 0
  )
}

/**
 * Verifica se sugestao pode ser criada
 */
export function canCreateSuggestion(tipo: string, descricao: string): boolean {
  return tipo.length > 0 && descricao.trim().length > 0
}

// =============================================================================
// Builders de URL
// =============================================================================

/**
 * Constroi URL de conversas com filtros
 */
export function buildConversationsUrl(
  baseUrl: string,
  filter: string,
  limit: number
): string {
  const params = new URLSearchParams()
  if (filter !== 'all') {
    params.append('avaliada', filter)
  }
  params.append('limit', String(limit))
  return `${baseUrl}?${params.toString()}`
}

/**
 * Constroi URL de sugestoes com filtro de status
 */
export function buildSuggestionsUrl(baseUrl: string, status: string): string {
  const params = new URLSearchParams()
  if (status !== 'all') {
    params.append('status', status)
  }
  return `${baseUrl}?${params.toString()}`
}

// =============================================================================
// Calculadores
// =============================================================================

/**
 * Calcula taxa de falha a partir da taxa de sucesso
 */
export function calculateFailureRate(successRate: number): number {
  return 100 - successRate
}

/**
 * Calcula score medio de uma avaliacao
 */
export function calculateAverageRating(ratings: {
  naturalidade: number
  persona: number
  objetivo: number
  satisfacao: number
}): number {
  const sum = ratings.naturalidade + ratings.persona + ratings.objetivo + ratings.satisfacao
  return sum / 4
}
