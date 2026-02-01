/**
 * Testes para GET /api/admin/conversas
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/admin/conversas/route'
import { NextRequest } from 'next/server'

// Mock fetch global
const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  mockFetch.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function createRequest(searchParams: string = '') {
  const url = `http://localhost:3000/api/admin/conversas${searchParams ? `?${searchParams}` : ''}`
  return new NextRequest(url, { method: 'GET' })
}

describe('GET /api/admin/conversas', () => {
  it('deve retornar lista de conversas', async () => {
    const mockData = {
      conversas: [
        {
          id: 'conv1',
          medico_nome: 'Dr. Silva',
          total_mensagens: 10,
          status: 'ativa',
          avaliada: false,
          criada_em: '2024-01-15T10:00:00Z',
        },
      ],
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.conversas).toHaveLength(1)
    expect(data.conversas[0].medico_nome).toBe('Dr. Silva')
  })

  it('deve passar query params para backend', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conversas: [] }),
    })

    const request = createRequest('avaliada=false&limit=10')
    await GET(request)

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('avaliada=false')
    expect(calledUrl).toContain('limit=10')
  })

  it('deve incluir header de autorizacao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conversas: [] }),
    })

    const request = createRequest()
    await GET(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    expect(calledOptions.headers).toBeDefined()
    expect((calledOptions.headers as Record<string, string>).Authorization).toContain('Bearer')
  })

  it('deve retornar erro 500 quando backend falha', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Erro interno' }),
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Erro interno')
  })

  it('deve tratar erro de rede', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Network error')
  })

  it('deve retornar lista vazia quando backend retorna vazio', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conversas: [] }),
    })

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.conversas).toHaveLength(0)
  })
})
