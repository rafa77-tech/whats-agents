/**
 * Schemas Zod para o modulo de Instrucoes (Diretrizes)
 */

import { z } from 'zod'

// =============================================================================
// Schemas base
// =============================================================================

/**
 * Schema para tipo de diretriz
 */
export const tipoDiretrizSchema = z.enum(['margem_negociacao', 'regra_especial', 'info_adicional'])

/**
 * Schema para escopo
 */
export const escopoSchema = z.enum(['vaga', 'medico', 'hospital', 'especialidade', 'global'])

/**
 * Schema para status
 */
export const statusSchema = z.enum(['ativa', 'expirada', 'cancelada'])

// =============================================================================
// Schema de conteudo
// =============================================================================

/**
 * Schema para conteudo de diretriz
 */
export const diretrizConteudoSchema = z.object({
  valor_maximo: z.number().positive().optional(),
  percentual_maximo: z.number().positive().max(100).optional(),
  regra: z.string().min(1).max(1000).optional(),
  info: z.string().min(1).max(1000).optional(),
})

// =============================================================================
// Schema de query params
// =============================================================================

/**
 * Schema para query params de GET /api/diretrizes
 */
export const diretrizesQuerySchema = z.object({
  status: z.string().default('ativa'),
})

/**
 * Valida e parseia query params de diretrizes
 */
export function parseDiretrizesQuery(searchParams: URLSearchParams) {
  return diretrizesQuerySchema.parse({
    status: searchParams.get('status') || 'ativa',
  })
}

// =============================================================================
// Schema de criacao
// =============================================================================

/**
 * Schema para criar diretriz
 */
export const criarDiretrizSchema = z
  .object({
    tipo: tipoDiretrizSchema,
    escopo: escopoSchema,
    conteudo: diretrizConteudoSchema,
    hospital_id: z.string().uuid().optional(),
    especialidade_id: z.string().uuid().optional(),
    vaga_id: z.string().uuid().optional(),
    cliente_id: z.string().uuid().optional(),
    expira_em: z.string().datetime().optional(),
  })
  .refine(
    (data) => {
      // Validar que escopo hospital tem hospital_id
      if (data.escopo === 'hospital' && !data.hospital_id) {
        return false
      }
      return true
    },
    { message: 'hospital_id é obrigatório para escopo hospital' }
  )
  .refine(
    (data) => {
      // Validar que escopo especialidade tem especialidade_id
      if (data.escopo === 'especialidade' && !data.especialidade_id) {
        return false
      }
      return true
    },
    { message: 'especialidade_id é obrigatório para escopo especialidade' }
  )
  .refine(
    (data) => {
      // Validar conteudo baseado no tipo
      if (data.tipo === 'margem_negociacao') {
        return data.conteudo.valor_maximo || data.conteudo.percentual_maximo
      }
      if (data.tipo === 'regra_especial') {
        return !!data.conteudo.regra
      }
      if (data.tipo === 'info_adicional') {
        return !!data.conteudo.info
      }
      return true
    },
    { message: 'Conteúdo inválido para o tipo de diretriz' }
  )

// =============================================================================
// Schema de atualizacao
// =============================================================================

/**
 * Schema para cancelar diretriz (PATCH)
 */
export const cancelarDiretrizSchema = z.object({
  status: z.literal('cancelada'),
})

// =============================================================================
// Schema de resposta
// =============================================================================

/**
 * Schema para diretriz retornada pela API
 */
export const diretrizSchema = z.object({
  id: z.string().uuid(),
  tipo: tipoDiretrizSchema,
  escopo: escopoSchema,
  vaga_id: z.string().uuid().nullable().optional(),
  cliente_id: z.string().uuid().nullable().optional(),
  hospital_id: z.string().uuid().nullable().optional(),
  especialidade_id: z.string().uuid().nullable().optional(),
  conteudo: diretrizConteudoSchema,
  criado_por: z.string(),
  criado_em: z.string(),
  expira_em: z.string().nullable().optional(),
  status: statusSchema,
  vagas: z
    .object({
      data: z.string(),
      hospital_id: z.string(),
    })
    .nullable()
    .optional(),
  clientes: z
    .object({
      primeiro_nome: z.string(),
      sobrenome: z.string(),
      telefone: z.string(),
    })
    .nullable()
    .optional(),
  hospitais: z
    .object({
      nome: z.string(),
    })
    .nullable()
    .optional(),
  especialidades: z
    .object({
      nome: z.string(),
    })
    .nullable()
    .optional(),
})

/**
 * Tipo inferido do schema de diretriz
 */
export type DiretrizFromSchema = z.infer<typeof diretrizSchema>

// =============================================================================
// Tipos inferidos
// =============================================================================

export type TipoDiretrizEnum = z.infer<typeof tipoDiretrizSchema>
export type EscopoEnum = z.infer<typeof escopoSchema>
export type StatusEnum = z.infer<typeof statusSchema>
export type CriarDiretrizInput = z.input<typeof criarDiretrizSchema>
export type CancelarDiretrizInput = z.infer<typeof cancelarDiretrizSchema>
