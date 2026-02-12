/**
 * Testes para GET /api/sistema/status
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock shouldUseMock
vi.mock('@/lib/mock', () => ({
  shouldUseMock: vi.fn(() => false),
  mockSistemaStatus: {
    pilot_mode: true,
    autonomous_features: {
      discovery_automatico: false,
      oferta_automatica: false,
      reativacao_automatica: false,
      feedback_automatico: false,
    },
  },
}))

describe('GET /api/sistema/status', () => {
  const originalFetch = global.fetch
  let mockFetch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.resetModules()
    mockFetch = vi.fn()
    global.fetch = mockFetch as unknown as typeof fetch
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.clearAllMocks()
  })

  it('deve retornar status do sistema quando backend responde', async () => {
    const mockStatus = {
      pilot_mode: false,
      autonomous_features: {
        discovery_automatico: true,
        oferta_automatica: true,
        reativacao_automatica: false,
        feedback_automatico: false,
      },
      last_changed_by: 'admin@test.com',
      last_changed_at: '2026-01-30T10:00:00Z',
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockStatus),
    })

    const { GET } = await import('@/app/api/sistema/status/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockStatus)
  })

  it('deve retornar erro 503 quando backend falha', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const { GET } = await import('@/app/api/sistema/status/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(503)
    expect(data.error).toContain('Backend indisponivel')
  })

  it('deve retornar erro 503 quando fetch lanca excecao', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    const { GET } = await import('@/app/api/sistema/status/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(503)
    expect(data.error).toContain('Backend indisponivel')
  })

  it('deve retornar dados mock quando shouldUseMock retorna true', async () => {
    const { shouldUseMock } = await import('@/lib/mock')
    vi.mocked(shouldUseMock).mockReturnValueOnce(true)

    const { GET } = await import('@/app/api/sistema/status/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.pilot_mode).toBe(true)
    expect(mockFetch).not.toHaveBeenCalled()
  })
})
