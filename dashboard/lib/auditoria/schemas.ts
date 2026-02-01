/**
 * Schemas Zod para validacao do modulo de Auditoria
 */

import { z } from 'zod'

// =============================================================================
// Constantes de validacao
// =============================================================================

export const VALID_ACTIONS = [
  'julia_toggle',
  'julia_pause',
  'feature_flag_update',
  'rate_limit_update',
  'manual_handoff',
  'return_to_julia',
  'circuit_reset',
  'create_campaign',
  'start_campaign',
  'pause_campaign',
] as const

// =============================================================================
// Query Params Schemas
// =============================================================================

/**
 * Schema para query params de GET /api/auditoria
 */
export const auditLogsQuerySchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  per_page: z.coerce.number().int().positive().max(100).default(50),
  action: z.string().optional(),
  actor_email: z.string().max(255).optional(),
  from_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)')
    .optional(),
  to_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)')
    .optional(),
})

export type AuditLogsQueryParams = z.infer<typeof auditLogsQuerySchema>

/**
 * Schema para query params de GET /api/auditoria/export
 */
export const auditExportQuerySchema = z.object({
  action: z.string().optional(),
  actor_email: z.string().max(255).optional(),
  from_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)')
    .optional(),
  to_date: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)')
    .optional(),
})

export type AuditExportQueryParams = z.infer<typeof auditExportQuerySchema>

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Parse query params de listagem de logs
 */
export function parseAuditLogsQuery(searchParams: URLSearchParams): AuditLogsQueryParams {
  const params: Record<string, string> = {}

  const page = searchParams.get('page')
  const perPage = searchParams.get('per_page')
  const action = searchParams.get('action')
  const actorEmail = searchParams.get('actor_email')
  const fromDate = searchParams.get('from_date')
  const toDate = searchParams.get('to_date')

  if (page) params.page = page
  if (perPage) params.per_page = perPage
  if (action) params.action = action
  if (actorEmail) params.actor_email = actorEmail
  if (fromDate) params.from_date = fromDate
  if (toDate) params.to_date = toDate

  return auditLogsQuerySchema.parse(params)
}

/**
 * Parse query params de export
 */
export function parseAuditExportQuery(searchParams: URLSearchParams): AuditExportQueryParams {
  const params: Record<string, string> = {}

  const action = searchParams.get('action')
  const actorEmail = searchParams.get('actor_email')
  const fromDate = searchParams.get('from_date')
  const toDate = searchParams.get('to_date')

  if (action) params.action = action
  if (actorEmail) params.actor_email = actorEmail
  if (fromDate) params.from_date = fromDate
  if (toDate) params.to_date = toDate

  return auditExportQuerySchema.parse(params)
}
