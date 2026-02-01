/**
 * Testes para GET /api/sistema/config
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// Mock shouldUseMock
vi.mock('@/lib/mock', () => ({
  shouldUseMock: vi.fn(() => false),
  mockSistemaConfig: {
    rate_limit: {
      mensagens_por_hora: 20,
      mensagens_por_dia: 100,
      intervalo_minimo_segundos: 45,
    },
  },
}))

describe('GET /api/sistema/config', () => {
  const originalFetch = global.fetch
  let mockFetch: ReturnType<typeof vi.fn>

  beforeEach(() => {
    vi.resetModules()
    mockFetch = vi.fn()
    global.fetch = mockFetch
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.clearAllMocks()
  })

  it('deve retornar config formatada quando backend responde', async () => {
    const backendResponse = {
      rate_limit: {
        msgs_hora: 12,
        limite_hora: 20,
        msgs_dia: 45,
        limite_dia: 100,
        horario_permitido: true,
        hora_atual: '14:30',
      },
    }

    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(backendResponse),
    })

    const { GET } = await import('@/app/api/sistema/config/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.rate_limit).toEqual({
      msgs_por_hora: 20,
      msgs_por_dia: 100,
      intervalo_min: 45,
      intervalo_max: 180,
    })
    expect(data.horario).toEqual({
      inicio: 8,
      fim: 20,
      dias: 'Segunda a Sexta',
    })
    expect(data.uso_atual).toEqual({
      msgs_hora: 12,
      msgs_dia: 45,
      horario_permitido: true,
      hora_atual: '14:30',
    })
  })

  it('deve retornar erro 503 quando backend falha', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
    })

    const { GET } = await import('@/app/api/sistema/config/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(503)
    expect(data.error).toContain('Backend indisponivel')
  })

  it('deve retornar erro 503 quando fetch lanca excecao', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    const { GET } = await import('@/app/api/sistema/config/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(503)
    expect(data.error).toContain('Backend indisponivel')
  })

  it('deve retornar dados mock quando shouldUseMock retorna true', async () => {
    const { shouldUseMock } = await import('@/lib/mock')
    vi.mocked(shouldUseMock).mockReturnValueOnce(true)

    const { GET } = await import('@/app/api/sistema/config/route')
    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.rate_limit.msgs_por_hora).toBe(20)
    expect(mockFetch).not.toHaveBeenCalled()
  })
})
