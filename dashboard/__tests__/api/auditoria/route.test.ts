/**
 * Testes para GET /api/auditoria
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/auditoria/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient
const mockSelect = vi.fn()
const mockEq = vi.fn()
const mockIlike = vi.fn()
const mockGte = vi.fn()
const mockLte = vi.fn()
const mockOrder = vi.fn()
const mockRange = vi.fn()
const mockFrom = vi.fn()

const mockSupabase = {
  from: mockFrom,
}

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

function createRequest(searchParams: string = '') {
  const url = `http://localhost:3000/api/auditoria${searchParams ? `?${searchParams}` : ''}`
  return new NextRequest(url, { method: 'GET' })
}

describe('GET /api/auditoria', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup chain
    mockFrom.mockReturnValue({ select: mockSelect })
    mockSelect.mockReturnValue({
      eq: mockEq,
      ilike: mockIlike,
      gte: mockGte,
      lte: mockLte,
      order: mockOrder,
    })
    mockEq.mockReturnValue({
      ilike: mockIlike,
      gte: mockGte,
      lte: mockLte,
      order: mockOrder,
    })
    mockIlike.mockReturnValue({
      gte: mockGte,
      lte: mockLte,
      order: mockOrder,
    })
    mockGte.mockReturnValue({
      lte: mockLte,
      order: mockOrder,
    })
    mockLte.mockReturnValue({
      order: mockOrder,
    })
    mockOrder.mockReturnValue({ range: mockRange })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista de logs', async () => {
    const mockLogs = [
      {
        id: 'log1',
        action: 'julia_toggle',
        user_email: 'admin@example.com',
        details: { role: 'admin', enabled: true },
        created_at: '2024-01-15T10:00:00Z',
      },
    ]

    mockRange.mockResolvedValue({
      data: mockLogs,
      error: null,
      count: 1,
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toHaveLength(1)
    expect(data.data[0].action).toBe('julia_toggle')
    expect(data.data[0].actor_email).toBe('admin@example.com')
    expect(data.total).toBe(1)
  })

  it('deve aplicar filtro de action', async () => {
    mockRange.mockResolvedValue({
      data: [],
      error: null,
      count: 0,
    })

    const request = createRequest('action=manual_handoff')
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('action', 'manual_handoff')
  })

  it('deve aplicar filtro de actor_email', async () => {
    mockRange.mockResolvedValue({
      data: [],
      error: null,
      count: 0,
    })

    const request = createRequest('actor_email=admin')
    await GET(request)

    expect(mockIlike).toHaveBeenCalledWith('user_email', '%admin%')
  })

  it('deve aplicar filtro de from_date', async () => {
    mockRange.mockResolvedValue({
      data: [],
      error: null,
      count: 0,
    })

    const request = createRequest('from_date=2024-01-01')
    await GET(request)

    expect(mockGte).toHaveBeenCalledWith('created_at', '2024-01-01')
  })

  it('deve aplicar filtro de to_date', async () => {
    mockRange.mockResolvedValue({
      data: [],
      error: null,
      count: 0,
    })

    const request = createRequest('to_date=2024-01-31')
    await GET(request)

    expect(mockLte).toHaveBeenCalledWith('created_at', '2024-01-31')
  })

  it('deve aplicar paginacao', async () => {
    mockRange.mockResolvedValue({
      data: [],
      error: null,
      count: 100,
    })

    const request = createRequest('page=2&per_page=25')
    await GET(request)

    // page=2, per_page=25 -> from=25, to=49
    expect(mockRange).toHaveBeenCalledWith(25, 49)
  })

  it('deve calcular total de paginas', async () => {
    mockRange.mockResolvedValue({
      data: [],
      error: null,
      count: 120,
    })

    const request = createRequest('per_page=50')
    const response = await GET(request)
    const data = await response.json()

    expect(data.pages).toBe(3) // 120/50 = 2.4 -> 3
  })

  it('deve transformar dados corretamente', async () => {
    const mockLogs = [
      {
        id: 'log1',
        action: 'create_campaign',
        user_email: null,
        details: {},
        created_at: '2024-01-15T10:00:00Z',
      },
    ]

    mockRange.mockResolvedValue({
      data: mockLogs,
      error: null,
      count: 1,
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(data.data[0].actor_email).toBe('system')
    expect(data.data[0].actor_role).toBe('unknown')
  })

  it('deve retornar array vazio em caso de erro', async () => {
    mockRange.mockResolvedValue({
      data: null,
      error: { message: 'Database error' },
      count: 0,
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toEqual([])
    expect(data.total).toBe(0)
  })

  it('deve ordenar por created_at descendente', async () => {
    mockRange.mockResolvedValue({
      data: [],
      error: null,
      count: 0,
    })

    const request = createRequest()
    await GET(request)

    expect(mockOrder).toHaveBeenCalledWith('created_at', { ascending: false })
  })
})
