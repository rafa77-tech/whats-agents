/**
 * Schemas Zod para validacao do modulo de Qualidade
 */

import { z } from 'zod'

// =============================================================================
// Constantes de validacao
// =============================================================================

export const VALID_SUGGESTION_STATUSES = ['pending', 'approved', 'rejected', 'implemented'] as const
export const VALID_SUGGESTION_TYPES = ['tom', 'resposta', 'abertura', 'objecao'] as const
export const VALID_CONVERSATION_FILTERS = ['all', 'true', 'false'] as const

// =============================================================================
// Query Params Schemas
// =============================================================================

/**
 * Schema para query params de GET /api/admin/conversas
 */
export const conversationsQuerySchema = z.object({
  avaliada: z.enum(['true', 'false']).optional(),
  limit: z.coerce.number().int().positive().max(100).default(20),
})

export type ConversationsQueryParams = z.infer<typeof conversationsQuerySchema>

/**
 * Schema para query params de GET /api/admin/sugestoes
 */
export const suggestionsQuerySchema = z.object({
  status: z.enum(VALID_SUGGESTION_STATUSES).optional(),
})

export type SuggestionsQueryParams = z.infer<typeof suggestionsQuerySchema>

// =============================================================================
// Body Schemas
// =============================================================================

/**
 * Schema para body de POST /api/admin/avaliacoes
 */
export const createEvaluationSchema = z.object({
  conversa_id: z.string().uuid('ID de conversa invalido'),
  naturalidade: z.number().int().min(1).max(5),
  persona: z.number().int().min(1).max(5),
  objetivo: z.number().int().min(1).max(5),
  satisfacao: z.number().int().min(1).max(5),
  observacoes: z.string().max(2000).default(''),
})

export type CreateEvaluationBody = z.infer<typeof createEvaluationSchema>

/**
 * Schema para body de POST /api/admin/sugestoes
 */
export const createSuggestionSchema = z.object({
  tipo: z.enum(VALID_SUGGESTION_TYPES, {
    errorMap: () => ({ message: 'Tipo de sugestao invalido' }),
  }),
  descricao: z.string().min(10, 'Descricao deve ter pelo menos 10 caracteres').max(2000),
  exemplos: z.string().max(2000).optional(),
})

export type CreateSuggestionBody = z.infer<typeof createSuggestionSchema>

/**
 * Schema para body de PATCH /api/admin/sugestoes/[id]
 */
export const updateSuggestionSchema = z.object({
  status: z.enum(VALID_SUGGESTION_STATUSES, {
    errorMap: () => ({ message: 'Status invalido' }),
  }),
})

export type UpdateSuggestionBody = z.infer<typeof updateSuggestionSchema>

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Parse query params de conversas
 */
export function parseConversationsQuery(searchParams: URLSearchParams): ConversationsQueryParams {
  const params: Record<string, string> = {}
  const avaliada = searchParams.get('avaliada')
  const limit = searchParams.get('limit')

  if (avaliada) params.avaliada = avaliada
  if (limit) params.limit = limit

  return conversationsQuerySchema.parse(params)
}

/**
 * Parse query params de sugestoes
 */
export function parseSuggestionsQuery(searchParams: URLSearchParams): SuggestionsQueryParams {
  const params: Record<string, string> = {}
  const status = searchParams.get('status')

  if (status) params.status = status

  return suggestionsQuerySchema.parse(params)
}

/**
 * Parse body de criacao de avaliacao
 */
export function parseCreateEvaluationBody(body: unknown): CreateEvaluationBody {
  return createEvaluationSchema.parse(body)
}

/**
 * Parse body de criacao de sugestao
 */
export function parseCreateSuggestionBody(body: unknown): CreateSuggestionBody {
  return createSuggestionSchema.parse(body)
}

/**
 * Parse body de atualizacao de sugestao
 */
export function parseUpdateSuggestionBody(body: unknown): UpdateSuggestionBody {
  return updateSuggestionSchema.parse(body)
}
