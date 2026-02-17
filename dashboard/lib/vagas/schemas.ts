/**
 * Zod schemas for /vagas validation
 */

import { z } from 'zod'
import type { ShiftStatus } from './types'

/**
 * Valid shift statuses
 */
export const VALID_STATUSES: ShiftStatus[] = [
  'aberta',
  'reservada',
  'confirmada',
  'cancelada',
  'realizada',
  'fechada',
]

/**
 * Schema for GET /api/vagas query params
 */
export const shiftListParamsSchema = z.object({
  page: z.coerce.number().int().positive().default(1),
  per_page: z.coerce.number().int().positive().max(500).default(20),
  status: z
    .enum(['aberta', 'reservada', 'confirmada', 'cancelada', 'realizada', 'fechada'])
    .optional(),
  criticidade: z.enum(['normal', 'urgente', 'critica']).optional(),
  hospital_id: z.string().uuid().optional(),
  especialidade_id: z.string().uuid().optional(),
  date_from: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)')
    .optional(),
  date_to: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)')
    .optional(),
  search: z.string().max(200).optional(),
})

export type ShiftListParams = z.infer<typeof shiftListParamsSchema>

/**
 * Schema for PATCH /api/vagas/[id] body
 */
export const shiftUpdateSchema = z.object({
  cliente_id: z.string().uuid().nullable().optional(),
  status: z
    .enum(['aberta', 'reservada', 'confirmada', 'cancelada', 'realizada', 'fechada'])
    .optional(),
  criticidade: z.enum(['normal', 'urgente', 'critica']).optional(),
  hospital_id: z.string().uuid().optional(),
  especialidade_id: z.string().uuid().optional(),
  data: z
    .string()
    .regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)')
    .optional(),
  hora_inicio: z.preprocess(
    (v) => (v === '' ? null : v),
    z
      .string()
      .regex(/^\d{2}:\d{2}$/, 'Formato de hora invalido (HH:MM)')
      .nullable()
      .optional()
  ),
  hora_fim: z.preprocess(
    (v) => (v === '' ? null : v),
    z
      .string()
      .regex(/^\d{2}:\d{2}$/, 'Formato de hora invalido (HH:MM)')
      .nullable()
      .optional()
  ),
  valor: z.preprocess(
    (v) => (v === '' || v === 0 ? null : v),
    z.number().int().positive().nullable().optional()
  ),
  contato_nome: z.preprocess(
    (v) => (v === '' ? null : v),
    z.string().min(2, 'Nome do contato deve ter pelo menos 2 caracteres').nullable().optional()
  ),
  contato_whatsapp: z.preprocess(
    (v) => (v === '' ? null : v),
    z
      .string()
      .regex(/^\d{10,13}$/, 'WhatsApp invalido (apenas numeros, 10-13 digitos)')
      .nullable()
      .optional()
  ),
})

export type ShiftUpdateBody = z.infer<typeof shiftUpdateSchema>

/**
 * Parse and validate shift list query params from URLSearchParams
 * @param searchParams - URL search params
 * @returns Parsed and validated params
 */
export function parseShiftListParams(searchParams: URLSearchParams): ShiftListParams {
  const raw: Record<string, string | undefined> = {}

  // Only include params that are present
  const page = searchParams.get('page')
  const perPage = searchParams.get('per_page')
  const status = searchParams.get('status')
  const hospitalId = searchParams.get('hospital_id')
  const especialidadeId = searchParams.get('especialidade_id')
  const dateFrom = searchParams.get('date_from')
  const dateTo = searchParams.get('date_to')
  const search = searchParams.get('search')
  const criticidade = searchParams.get('criticidade')

  if (page) raw.page = page
  if (perPage) raw.per_page = perPage
  if (status) raw.status = status
  if (criticidade) raw.criticidade = criticidade
  if (hospitalId) raw.hospital_id = hospitalId
  if (especialidadeId) raw.especialidade_id = especialidadeId
  if (dateFrom) raw.date_from = dateFrom
  if (dateTo) raw.date_to = dateTo
  if (search) raw.search = search

  return shiftListParamsSchema.parse(raw)
}

/**
 * Parse and validate shift update body
 * @param body - Request body
 * @returns Parsed and validated body
 */
export function parseShiftUpdateBody(body: unknown): ShiftUpdateBody {
  return shiftUpdateSchema.parse(body)
}

/**
 * Schema for POST /api/vagas body (manual shift creation)
 */
export const shiftCreateSchema = z.object({
  hospital_id: z.string().uuid(),
  especialidade_id: z.string().uuid(),
  data: z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Formato de data invalido (YYYY-MM-DD)'),
  hora_inicio: z
    .string()
    .regex(/^\d{2}:\d{2}$/, 'Formato de hora invalido (HH:MM)')
    .optional(),
  hora_fim: z
    .string()
    .regex(/^\d{2}:\d{2}$/, 'Formato de hora invalido (HH:MM)')
    .optional(),
  valor: z.number().int().positive().optional(),
  observacoes: z.string().max(500).optional(),
  criticidade: z.enum(['normal', 'urgente', 'critica']).optional(),
  quantidade: z.coerce.number().int().min(1).max(50).optional(),
  contato_nome: z.string().min(2, 'Nome do contato deve ter pelo menos 2 caracteres'),
  contato_whatsapp: z
    .string()
    .regex(/^\d{10,13}$/, 'WhatsApp invalido (apenas numeros, 10-13 digitos)'),
})

export type ShiftCreateBody = z.infer<typeof shiftCreateSchema>

/**
 * Parse and validate shift create body
 * @param body - Request body
 * @returns Parsed and validated body
 */
export function parseShiftCreateBody(body: unknown): ShiftCreateBody {
  return shiftCreateSchema.parse(body)
}
