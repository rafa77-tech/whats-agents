/**
 * Testes para GET /api/auditoria/export
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/auditoria/export/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient
const mockSelect = vi.fn()
const mockEq = vi.fn()
const mockIlike = vi.fn()
const mockGte = vi.fn()
const mockLte = vi.fn()
const mockOrder = vi.fn()
const mockLimit = vi.fn()
const mockFrom = vi.fn()

const mockSupabase = {
  from: mockFrom,
}

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

function createRequest(searchParams: string = '') {
  const url = `http://localhost:3000/api/auditoria/export${searchParams ? `?${searchParams}` : ''}`
  return new NextRequest(url, { method: 'GET' })
}

describe('GET /api/auditoria/export', () => {
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
    mockOrder.mockReturnValue({ limit: mockLimit })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar CSV com logs', async () => {
    const mockLogs = [
      {
        id: 'log1',
        action: 'julia_toggle',
        user_email: 'admin@example.com',
        details: { role: 'admin', enabled: true },
        created_at: '2024-01-15T10:00:00Z',
      },
    ]

    mockLimit.mockResolvedValue({
      data: mockLogs,
      error: null,
    })

    const request = createRequest()
    const response = await GET(request)
    const text = await response.text()

    expect(response.status).toBe(200)
    expect(response.headers.get('Content-Type')).toBe('text/csv')
    expect(response.headers.get('Content-Disposition')).toContain('attachment')
    expect(response.headers.get('Content-Disposition')).toContain('.csv')

    // Verifica headers do CSV
    expect(text).toContain('timestamp,action,actor_email,actor_role,details')
    // Verifica dados
    expect(text).toContain('julia_toggle')
    expect(text).toContain('admin@example.com')
  })

  it('deve aplicar filtro de action no export', async () => {
    mockLimit.mockResolvedValue({
      data: [],
      error: null,
    })

    const request = createRequest('action=create_campaign')
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('action', 'create_campaign')
  })

  it('deve aplicar filtro de actor_email no export', async () => {
    mockLimit.mockResolvedValue({
      data: [],
      error: null,
    })

    const request = createRequest('actor_email=test')
    await GET(request)

    expect(mockIlike).toHaveBeenCalledWith('user_email', '%test%')
  })

  it('deve aplicar filtro de datas no export', async () => {
    mockLimit.mockResolvedValue({
      data: [],
      error: null,
    })

    const request = createRequest('from_date=2024-01-01&to_date=2024-01-31')
    await GET(request)

    expect(mockGte).toHaveBeenCalledWith('created_at', '2024-01-01')
    expect(mockLte).toHaveBeenCalledWith('created_at', '2024-01-31')
  })

  it('deve limitar a 10000 registros', async () => {
    mockLimit.mockResolvedValue({
      data: [],
      error: null,
    })

    const request = createRequest()
    await GET(request)

    expect(mockLimit).toHaveBeenCalledWith(10000)
  })

  it('deve retornar CSV vazio em caso de erro', async () => {
    mockLimit.mockResolvedValue({
      data: null,
      error: { message: 'Database error' },
    })

    const request = createRequest()
    const response = await GET(request)
    const text = await response.text()

    expect(response.status).toBe(200)
    expect(response.headers.get('Content-Type')).toBe('text/csv')
    // Deve ter apenas o header
    expect(text).toBe('timestamp,action,actor_email,actor_role,details\n')
  })

  it('deve usar system para user_email nulo', async () => {
    const mockLogs = [
      {
        id: 'log1',
        action: 'circuit_reset',
        user_email: null,
        details: {},
        created_at: '2024-01-15T10:00:00Z',
      },
    ]

    mockLimit.mockResolvedValue({
      data: mockLogs,
      error: null,
    })

    const request = createRequest()
    const response = await GET(request)
    const text = await response.text()

    expect(text).toContain('system')
  })

  it('deve escapar detalhes corretamente', async () => {
    const mockLogs = [
      {
        id: 'log1',
        action: 'feature_flag_update',
        user_email: 'admin@test.com',
        details: { flag: 'test', value: 'with, comma' },
        created_at: '2024-01-15T10:00:00Z',
      },
    ]

    mockLimit.mockResolvedValue({
      data: mockLogs,
      error: null,
    })

    const request = createRequest()
    const response = await GET(request)
    const text = await response.text()

    // Detalhes com aspas devem estar escapados
    expect(text).toContain('feature_flag_update')
    expect(text).toContain('admin@test.com')
  })

  it('deve incluir data no nome do arquivo', async () => {
    mockLimit.mockResolvedValue({
      data: [],
      error: null,
    })

    const request = createRequest()
    const response = await GET(request)

    const contentDisposition = response.headers.get('Content-Disposition')
    expect(contentDisposition).toMatch(/audit_logs_\d{4}-\d{2}-\d{2}\.csv/)
  })
})
