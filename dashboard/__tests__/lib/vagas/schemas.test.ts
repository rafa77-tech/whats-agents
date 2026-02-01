/**
 * Testes para lib/vagas/schemas.ts
 */

import { describe, it, expect } from 'vitest'
import { ZodError } from 'zod'
import {
  shiftListParamsSchema,
  shiftUpdateSchema,
  parseShiftListParams,
  parseShiftUpdateBody,
} from '@/lib/vagas/schemas'

// =============================================================================
// shiftListParamsSchema
// =============================================================================

describe('shiftListParamsSchema', () => {
  it('deve aceitar parametros validos', () => {
    const result = shiftListParamsSchema.parse({
      page: '2',
      per_page: '20',
      status: 'aberta',
      hospital_id: '550e8400-e29b-41d4-a716-446655440000',
      especialidade_id: '550e8400-e29b-41d4-a716-446655440001',
      date_from: '2024-01-01',
      date_to: '2024-01-31',
      search: 'cardio',
    })

    expect(result.page).toBe(2)
    expect(result.per_page).toBe(20)
    expect(result.status).toBe('aberta')
    expect(result.hospital_id).toBe('550e8400-e29b-41d4-a716-446655440000')
    expect(result.date_from).toBe('2024-01-01')
    expect(result.search).toBe('cardio')
  })

  it('deve usar valores default', () => {
    const result = shiftListParamsSchema.parse({})

    expect(result.page).toBe(1)
    expect(result.per_page).toBe(20)
    expect(result.status).toBeUndefined()
    expect(result.hospital_id).toBeUndefined()
  })

  it('deve rejeitar status invalido', () => {
    expect(() =>
      shiftListParamsSchema.parse({ status: 'invalid' })
    ).toThrow(ZodError)
  })

  it('deve rejeitar hospital_id invalido (nao UUID)', () => {
    expect(() =>
      shiftListParamsSchema.parse({ hospital_id: 'not-a-uuid' })
    ).toThrow(ZodError)
  })

  it('deve rejeitar especialidade_id invalido (nao UUID)', () => {
    expect(() =>
      shiftListParamsSchema.parse({ especialidade_id: '123' })
    ).toThrow(ZodError)
  })

  it('deve rejeitar date_from em formato invalido', () => {
    expect(() =>
      shiftListParamsSchema.parse({ date_from: '01-15-2024' })
    ).toThrow(ZodError)

    expect(() =>
      shiftListParamsSchema.parse({ date_from: '2024/01/15' })
    ).toThrow(ZodError)
  })

  it('deve rejeitar date_to em formato invalido', () => {
    expect(() =>
      shiftListParamsSchema.parse({ date_to: 'January 15, 2024' })
    ).toThrow(ZodError)
  })

  it('deve aceitar per_page ate 500', () => {
    const result = shiftListParamsSchema.parse({ per_page: '500' })
    expect(result.per_page).toBe(500)
  })

  it('deve rejeitar per_page acima de 500', () => {
    expect(() =>
      shiftListParamsSchema.parse({ per_page: '501' })
    ).toThrow(ZodError)
  })

  it('deve rejeitar page menor que 1', () => {
    expect(() =>
      shiftListParamsSchema.parse({ page: '0' })
    ).toThrow(ZodError)

    expect(() =>
      shiftListParamsSchema.parse({ page: '-1' })
    ).toThrow(ZodError)
  })

  it('deve aceitar todos os status validos', () => {
    const statuses = ['aberta', 'reservada', 'confirmada', 'cancelada', 'realizada', 'fechada']

    for (const status of statuses) {
      const result = shiftListParamsSchema.parse({ status })
      expect(result.status).toBe(status)
    }
  })

  it('deve truncar search muito longo', () => {
    const longSearch = 'a'.repeat(300)
    expect(() =>
      shiftListParamsSchema.parse({ search: longSearch })
    ).toThrow(ZodError)
  })
})

// =============================================================================
// parseShiftListParams
// =============================================================================

describe('parseShiftListParams', () => {
  it('deve parsear URLSearchParams corretamente', () => {
    const params = new URLSearchParams()
    params.set('page', '3')
    params.set('per_page', '50')
    params.set('status', 'confirmada')

    const result = parseShiftListParams(params)

    expect(result.page).toBe(3)
    expect(result.per_page).toBe(50)
    expect(result.status).toBe('confirmada')
  })

  it('deve ignorar parametros vazios', () => {
    const params = new URLSearchParams()
    params.set('page', '2')
    // status nao definido

    const result = parseShiftListParams(params)

    expect(result.page).toBe(2)
    expect(result.status).toBeUndefined()
  })

  it('deve lancar erro para parametros invalidos', () => {
    const params = new URLSearchParams()
    params.set('status', 'invalido')

    expect(() => parseShiftListParams(params)).toThrow(ZodError)
  })
})

// =============================================================================
// shiftUpdateSchema
// =============================================================================

describe('shiftUpdateSchema', () => {
  it('deve aceitar cliente_id valido', () => {
    const result = shiftUpdateSchema.parse({
      cliente_id: '550e8400-e29b-41d4-a716-446655440000',
    })

    expect(result.cliente_id).toBe('550e8400-e29b-41d4-a716-446655440000')
  })

  it('deve aceitar cliente_id null', () => {
    const result = shiftUpdateSchema.parse({
      cliente_id: null,
    })

    expect(result.cliente_id).toBeNull()
  })

  it('deve aceitar status valido', () => {
    const result = shiftUpdateSchema.parse({
      status: 'confirmada',
    })

    expect(result.status).toBe('confirmada')
  })

  it('deve aceitar body vazio', () => {
    const result = shiftUpdateSchema.parse({})

    expect(result.cliente_id).toBeUndefined()
    expect(result.status).toBeUndefined()
  })

  it('deve rejeitar cliente_id invalido', () => {
    expect(() =>
      shiftUpdateSchema.parse({ cliente_id: 'not-a-uuid' })
    ).toThrow(ZodError)
  })

  it('deve rejeitar status invalido', () => {
    expect(() =>
      shiftUpdateSchema.parse({ status: 'pending' })
    ).toThrow(ZodError)
  })

  it('deve aceitar ambos cliente_id e status', () => {
    const result = shiftUpdateSchema.parse({
      cliente_id: '550e8400-e29b-41d4-a716-446655440000',
      status: 'reservada',
    })

    expect(result.cliente_id).toBe('550e8400-e29b-41d4-a716-446655440000')
    expect(result.status).toBe('reservada')
  })
})

// =============================================================================
// parseShiftUpdateBody
// =============================================================================

describe('parseShiftUpdateBody', () => {
  it('deve parsear body corretamente', () => {
    const body = {
      cliente_id: '550e8400-e29b-41d4-a716-446655440000',
      status: 'confirmada',
    }

    const result = parseShiftUpdateBody(body)

    expect(result.cliente_id).toBe('550e8400-e29b-41d4-a716-446655440000')
    expect(result.status).toBe('confirmada')
  })

  it('deve lancar erro para body invalido', () => {
    const body = { status: 'invalid' }

    expect(() => parseShiftUpdateBody(body)).toThrow(ZodError)
  })

  it('deve aceitar body parcial', () => {
    const result = parseShiftUpdateBody({ status: 'cancelada' })

    expect(result.status).toBe('cancelada')
    expect(result.cliente_id).toBeUndefined()
  })
})
