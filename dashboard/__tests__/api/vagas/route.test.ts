/**
 * Testes para GET /api/vagas e POST /api/vagas
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, POST } from '@/app/api/vagas/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient
const mockSelect = vi.fn()
const mockInsert = vi.fn()
const mockIlike = vi.fn().mockResolvedValue({ data: [], error: null })
const mockSearchSelect = vi.fn(() => ({ ilike: mockIlike }))
const mockFrom = vi.fn((table: string) => {
  if (table === 'vagas') {
    return {
      select: mockSelect,
      insert: mockInsert,
    }
  }
  // hospitais / especialidades sub-queries for search
  return { select: mockSearchSelect }
})
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
        contato_nome: 'Maria Silva',
        contato_whatsapp: '5511999999999',
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
    expect(data.data[0].contato_nome).toBe('Maria Silva')
    expect(data.data[0].contato_whatsapp).toBe('5511999999999')
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

  it('searches by hospital/especialidade name via sub-queries', async () => {
    // Mock sub-queries returning matching IDs
    mockIlike.mockImplementation((_col: string, pattern: string) => {
      if (pattern === '%cardio%') {
        return Promise.resolve({ data: [{ id: 'esp-1' }], error: null })
      }
      return Promise.resolve({ data: [], error: null })
    })

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

    // Should query hospitais and especialidades for matching names
    expect(mockFrom).toHaveBeenCalledWith('hospitais')
    expect(mockFrom).toHaveBeenCalledWith('especialidades')
    expect(mockIlike).toHaveBeenCalledWith('nome', '%cardio%')
  })

  it('returns empty when search matches nothing', async () => {
    mockIlike.mockResolvedValue({ data: [], error: null })

    const request = createRequest({ search: 'zzzznotfound' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toEqual([])
    expect(data.total).toBe(0)
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
    expect(data.data[0].contato_nome).toBeNull()
    expect(data.data[0].contato_whatsapp).toBeNull()
  })
})

// =============================================================================
// POST /api/vagas
// =============================================================================

function createPostRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/vagas', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

const validCreateBody = {
  hospital_id: '550e8400-e29b-41d4-a716-446655440000',
  especialidade_id: '550e8400-e29b-41d4-a716-446655440001',
  data: '2024-03-15',
  contato_nome: 'Maria Silva',
  contato_whatsapp: '5511999999999',
}

describe('POST /api/vagas', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('creates a shift with required fields only', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'new-vaga-id' },
          error: null,
        }),
      }),
    })

    const request = createPostRequest(validCreateBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(201)
    expect(data.success).toBe(true)
    expect(data.id).toBe('new-vaga-id')

    // Verify insert was called with correct data
    expect(mockFrom).toHaveBeenCalledWith('vagas')
    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        hospital_id: '550e8400-e29b-41d4-a716-446655440000',
        especialidade_id: '550e8400-e29b-41d4-a716-446655440001',
        data: '2024-03-15',
        status: 'aberta',
        origem: 'manual',
        valor_tipo: 'a_combinar',
      })
    )
  })

  it('creates a shift with all optional fields', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'new-vaga-id' },
          error: null,
        }),
      }),
    })

    const body = {
      ...validCreateBody,
      hora_inicio: '08:00',
      hora_fim: '18:00',
      valor: 2500,
      observacoes: 'Plantao noturno',
    }

    const request = createPostRequest(body)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(201)
    expect(data.success).toBe(true)

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        hora_inicio: '08:00',
        hora_fim: '18:00',
        valor: 2500,
        valor_tipo: 'fixo',
        observacoes: 'Plantao noturno',
      })
    )
  })

  it('sets valor_tipo to fixo when valor is provided', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'new-id' },
          error: null,
        }),
      }),
    })

    const request = createPostRequest({ ...validCreateBody, valor: 1500 })
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({ valor: 1500, valor_tipo: 'fixo' })
    )
  })

  it('sets valor_tipo to a_combinar when valor is absent', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'new-id' },
          error: null,
        }),
      }),
    })

    const request = createPostRequest(validCreateBody)
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(expect.objectContaining({ valor_tipo: 'a_combinar' }))
  })

  it('returns 400 for missing required fields', async () => {
    const request = createPostRequest({ hospital_id: '550e8400-e29b-41d4-a716-446655440000' })
    const response = await POST(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.detail).toBe('Dados invalidos')
    expect(data.errors).toBeDefined()
  })

  it('returns 400 for invalid hospital_id', async () => {
    const request = createPostRequest({
      ...validCreateBody,
      hospital_id: 'not-a-uuid',
    })
    const response = await POST(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.detail).toBe('Dados invalidos')
  })

  it('returns 400 for invalid date format', async () => {
    const request = createPostRequest({
      ...validCreateBody,
      data: '15-03-2024',
    })
    const response = await POST(request)

    expect(response.status).toBe(400)
  })

  it('returns 400 for invalid hora_inicio format', async () => {
    const request = createPostRequest({
      ...validCreateBody,
      hora_inicio: '8:00',
    })
    const response = await POST(request)

    expect(response.status).toBe(400)
  })

  it('returns 500 on database error', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: null,
          error: { message: 'Foreign key violation' },
        }),
      }),
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createPostRequest(validCreateBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao criar vaga no banco')

    consoleSpy.mockRestore()
  })

  it('returns 500 on unexpected error', async () => {
    mockInsert.mockImplementation(() => {
      throw new Error('Unexpected')
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createPostRequest(validCreateBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro interno do servidor')

    consoleSpy.mockRestore()
  })

  it('always sets status to aberta and origem to manual', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'new-id' },
          error: null,
        }),
      }),
    })

    const request = createPostRequest(validCreateBody)
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        status: 'aberta',
        origem: 'manual',
      })
    )
  })

  it('includes created_at timestamp', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'new-id' },
          error: null,
        }),
      }),
    })

    const request = createPostRequest(validCreateBody)
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        created_at: expect.any(String),
      })
    )
  })

  it('includes contato_nome and contato_whatsapp in insert', async () => {
    mockInsert.mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { id: 'new-id' },
          error: null,
        }),
      }),
    })

    const request = createPostRequest(validCreateBody)
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        contato_nome: 'Maria Silva',
        contato_whatsapp: '5511999999999',
      })
    )
  })

  it('returns 400 when contato_nome is missing', async () => {
    const { contato_nome: _, ...body } = validCreateBody
    const request = createPostRequest(body)
    const response = await POST(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.detail).toBe('Dados invalidos')
  })

  it('returns 400 when contato_whatsapp is missing', async () => {
    const { contato_whatsapp: _, ...body } = validCreateBody
    const request = createPostRequest(body)
    const response = await POST(request)

    expect(response.status).toBe(400)
    const data = await response.json()
    expect(data.detail).toBe('Dados invalidos')
  })

  it('returns 400 for invalid contato_whatsapp format', async () => {
    const request = createPostRequest({
      ...validCreateBody,
      contato_whatsapp: 'abc123',
    })
    const response = await POST(request)

    expect(response.status).toBe(400)
  })
})
