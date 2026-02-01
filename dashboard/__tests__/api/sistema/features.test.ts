/**
 * Testes para POST /api/sistema/features/[feature]
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

describe('POST /api/sistema/features/[feature]', () => {
  const originalFetch = global.fetch
  let mockFetch: ReturnType<typeof vi.fn>

  function createRequest(body: object): NextRequest {
    return new NextRequest('http://localhost/api/sistema/features/discovery_automatico', {
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

  it('deve retornar 400 quando feature invalida', async () => {
    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    const response = await POST(createRequest({ enabled: true }), {
      params: Promise.resolve({ feature: 'invalid_feature' }),
    })
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.error).toContain('Feature invalida')
  })

  it('deve retornar 401 quando usuario nao autenticado', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null } })

    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    const response = await POST(createRequest({ enabled: true }), {
      params: Promise.resolve({ feature: 'discovery_automatico' }),
    })
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.error).toContain('Nao autorizado')
  })

  it('deve retornar 403 quando usuario nao e admin', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'user' } })

    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    const response = await POST(createRequest({ enabled: true }), {
      params: Promise.resolve({ feature: 'discovery_automatico' }),
    })
    const data = await response.json()

    expect(response.status).toBe(403)
    expect(data.error).toContain('Permissao negada')
  })

  it('deve retornar 400 quando enabled nao e boolean', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })

    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    const response = await POST(
      new NextRequest('http://localhost/api/sistema/features/discovery_automatico', {
        method: 'POST',
        body: JSON.stringify({ enabled: 'true' }),
        headers: { 'Content-Type': 'application/json' },
      }),
      { params: Promise.resolve({ feature: 'discovery_automatico' }) }
    )
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.error).toContain('enabled')
  })

  it('deve habilitar feature quando admin autenticado', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })
    mockInsert.mockResolvedValueOnce({ error: null })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          feature: 'discovery_automatico',
          enabled: true,
          pilot_mode: false,
          autonomous_features: { discovery_automatico: true },
        }),
    })

    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    const response = await POST(createRequest({ enabled: true }), {
      params: Promise.resolve({ feature: 'discovery_automatico' }),
    })
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(data.feature).toBe('discovery_automatico')
    expect(data.enabled).toBe(true)
  })

  it('deve desabilitar feature quando admin autenticado', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })
    mockInsert.mockResolvedValueOnce({ error: null })

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () =>
        Promise.resolve({
          success: true,
          feature: 'oferta_automatica',
          enabled: false,
          pilot_mode: false,
          autonomous_features: { oferta_automatica: false },
        }),
    })

    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    const response = await POST(createRequest({ enabled: false }), {
      params: Promise.resolve({ feature: 'oferta_automatica' }),
    })
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.enabled).toBe(false)
  })

  it('deve retornar erro 500 quando backend falha', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'admin@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })

    mockFetch.mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: 'Erro no backend' }),
    })

    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    const response = await POST(createRequest({ enabled: true }), {
      params: Promise.resolve({ feature: 'discovery_automatico' }),
    })
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toContain('Erro ao alterar feature')
  })

  it('deve aceitar todas as features validas', async () => {
    const validFeatures = [
      'discovery_automatico',
      'oferta_automatica',
      'reativacao_automatica',
      'feedback_automatico',
    ]

    for (const feature of validFeatures) {
      mockGetUser.mockResolvedValueOnce({
        data: { user: { id: 'user-1', email: 'admin@test.com' } },
      })
      mockSingle.mockResolvedValueOnce({ data: { role: 'admin' } })
      mockInsert.mockResolvedValueOnce({ error: null })

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true, feature, enabled: true }),
      })

      const { POST } = await import('@/app/api/sistema/features/[feature]/route')
      const response = await POST(createRequest({ enabled: true }), {
        params: Promise.resolve({ feature }),
      })

      expect(response.status).toBe(200)
    }
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

    const { POST } = await import('@/app/api/sistema/features/[feature]/route')
    await POST(createRequest({ enabled: true }), {
      params: Promise.resolve({ feature: 'discovery_automatico' }),
    })

    expect(mockInsert).toHaveBeenCalled()
  })
})
