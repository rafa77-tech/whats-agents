import { z } from 'zod'
import { NextResponse } from 'next/server'

/**
 * Schemas de validação Zod para API Routes.
 *
 * Sprint 44 T05.4: Adicionar Zod Validation em API Routes.
 */

// =============================================================================
// Query Parameters Schemas
// =============================================================================

/**
 * Schema para parâmetros de período (comum em métricas).
 */
export const periodQuerySchema = z.object({
  period: z.enum(['24h', '7d', '30d', '90d']).default('7d'),
})

/**
 * Schema para parâmetros de métricas do dashboard.
 */
export const metricsQuerySchema = z.object({
  period: z.enum(['24h', '7d', '30d', '90d']).default('7d'),
  tipo: z.string().optional(),
})

/**
 * Schema para parâmetros de paginação.
 */
export const paginationQuerySchema = z.object({
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
})

/**
 * Schema para parâmetros de listagem de chips.
 */
export const chipsListQuerySchema = z.object({
  status: z.enum(['ativo', 'quarentena', 'pausado', 'banido', 'inativo']).optional(),
  instancia: z.string().optional(),
  trust_min: z.coerce.number().min(0).max(100).optional(),
  trust_max: z.coerce.number().min(0).max(100).optional(),
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(100).default(20),
})

/**
 * Schema para parâmetros de listagem de alertas.
 */
export const alertsQuerySchema = z.object({
  limit: z.coerce.number().int().min(1).max(50).default(10),
  severidade: z.enum(['info', 'warning', 'error', 'critical']).optional(),
  resolvido: z
    .string()
    .transform((v) => v === 'true')
    .optional(),
})

/**
 * Schema para parâmetros de listagem de conversas.
 */
export const conversasQuerySchema = z.object({
  status: z.enum(['ativa', 'encerrada', 'handoff']).optional(),
  controlled_by: z.enum(['julia', 'human']).optional(),
  page: z.coerce.number().int().min(1).default(1),
  limit: z.coerce.number().int().min(1).max(50).default(20),
})

/**
 * Schema para parâmetros de funil.
 */
export const funnelQuerySchema = z.object({
  period: z.enum(['24h', '7d', '30d', '90d']).default('7d'),
  hospital_id: z.string().uuid().optional(),
})

// =============================================================================
// Request Body Schemas
// =============================================================================

/**
 * Schema para ação em chip.
 */
export const chipActionSchema = z.object({
  chipId: z.string().uuid(),
  action: z.enum(['activate', 'deactivate', 'pause', 'resume', 'promote', 'demote', 'quarantine']),
  reason: z.string().min(1).max(500).optional(),
})

/**
 * Schema para resolver alerta.
 */
export const resolveAlertSchema = z.object({
  alertId: z.string().uuid(),
  resolucao: z.string().min(1).max(1000).optional(),
})

/**
 * Schema para enviar mensagem.
 */
export const sendMessageSchema = z.object({
  conversaId: z.string().uuid(),
  mensagem: z.string().min(1).max(4000),
})

/**
 * Schema para transferir controle de conversa.
 */
export const transferControlSchema = z.object({
  conversaId: z.string().uuid(),
  para: z.enum(['julia', 'human']),
  motivo: z.string().min(1).max(500).optional(),
})

/**
 * Schema para criar diretriz.
 */
export const createDiretrizSchema = z.object({
  titulo: z.string().min(1).max(200),
  conteudo: z.string().min(1).max(5000),
  tipo: z.enum(['comportamento', 'conhecimento', 'restricao']),
  prioridade: z.coerce.number().int().min(0).max(100).default(50),
  ativa: z.boolean().default(true),
})

/**
 * Schema para atualizar diretriz.
 */
export const updateDiretrizSchema = createDiretrizSchema.partial()

/**
 * Schema para criar campanha.
 */
export const createCampanhaSchema = z.object({
  nome: z.string().min(1).max(200),
  tipo: z.enum(['discovery', 'oferta', 'reativacao', 'followup', 'custom']),
  template: z.string().min(1).max(2000),
  filtros: z
    .object({
      especialidades: z.array(z.string()).optional(),
      hospitais: z.array(z.string().uuid()).optional(),
      status: z.array(z.string()).optional(),
    })
    .optional(),
  agendamento: z
    .object({
      data_inicio: z.string().datetime().optional(),
      data_fim: z.string().datetime().optional(),
      horario_inicio: z.string().regex(/^\d{2}:\d{2}$/).optional(),
      horario_fim: z.string().regex(/^\d{2}:\d{2}$/).optional(),
    })
    .optional(),
})

// =============================================================================
// ID Parameters Schemas
// =============================================================================

/**
 * Schema para parâmetros de ID UUID.
 */
export const uuidParamSchema = z.object({
  id: z.string().uuid(),
})

/**
 * Schema para parâmetros de nome.
 */
export const nameParamSchema = z.object({
  name: z.string().min(1).max(100),
})

// =============================================================================
// Validation Helpers
// =============================================================================

/**
 * Valida query parameters e retorna erro ou dados validados.
 */
export function validateQuery<T extends z.ZodTypeAny>(
  schema: T,
  searchParams: URLSearchParams
): { success: true; data: z.infer<T> } | { success: false; response: NextResponse } {
  const params = Object.fromEntries(searchParams.entries())
  const result = schema.safeParse(params)

  if (!result.success) {
    return {
      success: false,
      response: NextResponse.json(
        {
          error: 'Parâmetros inválidos',
          details: result.error.flatten(),
        },
        { status: 400 }
      ),
    }
  }

  return { success: true, data: result.data }
}

/**
 * Valida request body e retorna erro ou dados validados.
 */
export async function validateBody<T extends z.ZodTypeAny>(
  schema: T,
  request: Request
): Promise<{ success: true; data: z.infer<T> } | { success: false; response: NextResponse }> {
  let body: unknown
  try {
    body = await request.json()
  } catch {
    return {
      success: false,
      response: NextResponse.json({ error: 'Body inválido (não é JSON)' }, { status: 400 }),
    }
  }

  const result = schema.safeParse(body)

  if (!result.success) {
    return {
      success: false,
      response: NextResponse.json(
        {
          error: 'Dados inválidos',
          details: result.error.flatten(),
        },
        { status: 400 }
      ),
    }
  }

  return { success: true, data: result.data }
}

/**
 * Valida parâmetros de rota e retorna erro ou dados validados.
 */
export function validateParams<T extends z.ZodTypeAny>(
  schema: T,
  params: Record<string, string>
): { success: true; data: z.infer<T> } | { success: false; response: NextResponse } {
  const result = schema.safeParse(params)

  if (!result.success) {
    return {
      success: false,
      response: NextResponse.json(
        {
          error: 'Parâmetros de rota inválidos',
          details: result.error.flatten(),
        },
        { status: 400 }
      ),
    }
  }

  return { success: true, data: result.data }
}
