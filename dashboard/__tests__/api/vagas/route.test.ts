/**
 * Testes para GET /api/vagas
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/vagas/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient
const mockSelect = vi.fn()
const mockFrom = vi.fn(() => ({
  select: mockSelect,
}))
const mockSupabase = {
  from: mockFrom,
}

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/vagas?${searchParams}`
  return new NextRequest(url)
}

describe('GET /api/vagas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns paginated shifts', async () => {
    const mockVagas = [
      {
        id: 'vaga1',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 1500,
        status: 'aberta',
        total_candidaturas: 2,
        created_at: '2024-01-10T10:00:00Z',
        hospital_id: 'h1',
        especialidade_id: 'e1',
        hospitais: { id: 'h1', nome: 'Hospital ABC' },
        especialidades: { id: 'e1', nome: 'Cardiologia' },
      },
    ]

    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: mockVagas,
          error: null,
          count: 1,
        }),
      }),
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toHaveLength(1)
    expect(data.data[0].hospital).toBe('Hospital ABC')
    expect(data.total).toBe(1)
    expect(data.pages).toBe(1)
  })

  it('filters by status', async () => {
    const mockEq = vi.fn().mockReturnThis()
    mockSelect.mockReturnValue({
      eq: mockEq,
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: [],
          error: null,
          count: 0,
        }),
      }),
    })

    const request = createRequest({ status: 'aberta' })
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('status', 'aberta')
  })

  it('filters by hospital_id', async () => {
    const mockEq = vi.fn().mockReturnThis()
    mockSelect.mockReturnValue({
      eq: mockEq,
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: [],
          error: null,
          count: 0,
        }),
      }),
    })

    const hospitalId = '550e8400-e29b-41d4-a716-446655440000'
    const request = createRequest({ hospital_id: hospitalId })
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('hospital_id', hospitalId)
  })

  it('filters by especialidade_id', async () => {
    const mockEq = vi.fn().mockReturnThis()
    mockSelect.mockReturnValue({
      eq: mockEq,
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: [],
          error: null,
          count: 0,
        }),
      }),
    })

    const especialidadeId = '550e8400-e29b-41d4-a716-446655440001'
    const request = createRequest({ especialidade_id: especialidadeId })
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('especialidade_id', especialidadeId)
  })

  it('filters by date range', async () => {
    const mockGte = vi.fn().mockReturnThis()
    const mockLte = vi.fn().mockReturnThis()
    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnThis(),
      gte: mockGte,
      lte: mockLte,
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: [],
          error: null,
          count: 0,
        }),
      }),
    })

    const request = createRequest({
      date_from: '2024-01-01',
      date_to: '2024-01-31',
    })
    await GET(request)

    expect(mockGte).toHaveBeenCalledWith('data', '2024-01-01')
    expect(mockLte).toHaveBeenCalledWith('data', '2024-01-31')
  })

  it('searches by hospital/especialidade name', async () => {
    const mockOr = vi.fn().mockReturnThis()
    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: mockOr,
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: [],
          error: null,
          count: 0,
        }),
      }),
    })

    const request = createRequest({ search: 'cardio' })
    await GET(request)

    expect(mockOr).toHaveBeenCalledWith(
      'hospitais.nome.ilike.%cardio%,especialidades.nome.ilike.%cardio%'
    )
  })

  it('returns empty array on error', async () => {
    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: null,
          error: { message: 'Database error' },
          count: 0,
        }),
      }),
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toEqual([])
    expect(data.total).toBe(0)
  })

  it('validates query params with Zod - invalid status returns 400', async () => {
    const request = createRequest({ status: 'invalid_status' })
    const response = await GET(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.error).toBe('Parametros de busca invalidos')
  })

  it('validates query params with Zod - invalid UUID returns 400', async () => {
    const request = createRequest({ hospital_id: 'not-a-uuid' })
    const response = await GET(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.error).toBe('Parametros de busca invalidos')
  })

  it('validates query params with Zod - invalid date format returns 400', async () => {
    const request = createRequest({ date_from: '01-15-2024' })
    const response = await GET(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.error).toBe('Parametros de busca invalidos')
  })

  it('applies pagination correctly', async () => {
    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: [],
          error: null,
          count: 100,
        }),
      }),
    })

    const request = createRequest({ page: '3', per_page: '10' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.pages).toBe(10) // 100 total / 10 per page
  })

  it('transforms data correctly', async () => {
    const mockVagas = [
      {
        id: 'vaga1',
        data: '2024-01-15',
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: null,
        status: null,
        total_candidaturas: null,
        created_at: '2024-01-10T10:00:00Z',
        hospital_id: null,
        especialidade_id: null,
        hospitais: null,
        especialidades: null,
      },
    ]

    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnThis(),
      gte: vi.fn().mockReturnThis(),
      lte: vi.fn().mockReturnThis(),
      or: vi.fn().mockReturnThis(),
      order: vi.fn().mockReturnValue({
        range: vi.fn().mockResolvedValue({
          data: mockVagas,
          error: null,
          count: 1,
        }),
      }),
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].hospital).toBe('N/A')
    expect(data.data[0].especialidade).toBe('N/A')
    expect(data.data[0].valor).toBe(0)
    expect(data.data[0].status).toBe('aberta')
    expect(data.data[0].reservas_count).toBe(0)
  })
})
