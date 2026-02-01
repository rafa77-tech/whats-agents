/**
 * Testes para POST /api/sistema/pilot-mode
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { NextRequest } from 'next/server'

// Mock Supabase client
const mockGetUser = vi.fn()
const mockSelect = vi.fn()
const mockEq = vi.fn()
const mockSingle = vi.fn()
const mockInsert = vi.fn()

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() =>
    Promise.resolve({
      auth: {
        getUser: mockGetUser,
      },
      from: vi.fn(() => ({
        select: mockSelect.mockReturnThis(),
        eq: mockEq.mockReturnThis(),
        single: mockSingle,
        insert: mockInsert,
      })),
    })
  ),
}))

describe('POST /api/sistema/pilot-mode', () => {
  const originalFetch = global.fetch
  let mockFetch: ReturnType<typeof vi.fn>

  function createRequest(body: object): NextRequest {
    return new NextRequest('http://localhost/api/sistema/pilot-mode', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  beforeEach(() => {
    vi.resetModules()
    mockFetch = vi.fn()
    global.fetch = mockFetch

    // Reset mocks
    mockGetUser.mockReset()
    mockSelect.mockReset()
    mockEq.mockReset()
    mockSingle.mockReset()
    mockInsert.mockReset()
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.clearAllMocks()
  })

  it('deve retornar 401 quando usuario nao autenticado', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null } })

    const { POST } = await import('@/app/api/sistema/pilot-mode/route')
    const response = await POST(createRequest({ pilot_mode: true }))
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.error).toContain('Nao autorizado')
  })

  it('deve retornar 403 quando usuario nao e admin', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'user' } })

    const { POST } = await import('@/app/api/sistema/pilot-mode/route')
    const response = await POST(createRequest({ pilot_mode: true }))
    const data = await response.json()

    expect(response.status).toBe(403)
    expect(data.error).toContain('Permissao negada')
  })

  it('deve ativar modo piloto quando admin autenticado', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })
    mockInsert.mockResolvedValueOnce({ error: null })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, pilot_mode: true }),
    })

    const { POST } = await import('@/app/api/sistema/pilot-mode/route')
    const response = await POST(createRequest({ pilot_mode: true }))
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/sistema/pilot-mode'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          pilot_mode: true,
          changed_by: 'admin@test.com',
        }),
      })
    )
  })

  it('deve desativar modo piloto quando admin autenticado', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })
    mockInsert.mockResolvedValueOnce({ error: null })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true, pilot_mode: false }),
    })

    const { POST } = await import('@/app/api/sistema/pilot-mode/route')
    const response = await POST(createRequest({ pilot_mode: false }))
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.pilot_mode).toBe(false)
  })

  it('deve retornar erro 500 quando backend falha', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })

    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const { POST } = await import('@/app/api/sistema/pilot-mode/route')
    const response = await POST(createRequest({ pilot_mode: true }))
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toContain('Erro ao alterar')
  })

  it('deve registrar audit log apos alteracao', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })
    mockInsert.mockResolvedValueOnce({ error: null })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    })

    const { POST } = await import('@/app/api/sistema/pilot-mode/route')
    await POST(createRequest({ pilot_mode: true }))

    expect(mockInsert).toHaveBeenCalled()
  })
})
