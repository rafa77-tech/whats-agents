/**
 * Testes para GET /api/admin/conversas/[id]
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/admin/conversas/[id]/route'
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

function createRequest() {
  return new NextRequest('http://localhost:3000/api/admin/conversas/conv123', { method: 'GET' })
}

function createParams(id: string = 'conv123') {
  return { params: Promise.resolve({ id }) }
}

describe('GET /api/admin/conversas/[id]', () => {
  it('deve retornar detalhes da conversa', async () => {
    const mockData = {
      id: 'conv123',
      medico_nome: 'Dr. Carlos',
      interacoes: [
        {
          id: 'msg1',
          remetente: 'julia',
          conteudo: 'Oi, tudo bem?',
          criada_em: '2024-01-15T10:00:00Z',
        },
        {
          id: 'msg2',
          remetente: 'medico',
          conteudo: 'Tudo sim!',
          criada_em: '2024-01-15T10:01:00Z',
        },
      ],
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const request = createRequest()
    const response = await GET(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.id).toBe('conv123')
    expect(data.medico_nome).toBe('Dr. Carlos')
    expect(data.interacoes).toHaveLength(2)
  })

  it('deve chamar backend com ID correto', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'conv456' }),
    })

    const request = createRequest()
    await GET(request, createParams('conv456'))

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('/admin/conversas/conv456')
  })

  it('deve incluir header de autorizacao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'conv123' }),
    })

    const request = createRequest()
    await GET(request, createParams())

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    expect(calledOptions.headers).toBeDefined()
    expect((calledOptions.headers as Record<string, string>).Authorization).toContain('Bearer')
  })

  it('deve retornar erro 500 quando conversa nao encontrada', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Conversa nao encontrada' }),
    })

    const request = createRequest()
    const response = await GET(request, createParams('inexistente'))
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Conversa nao encontrada')
  })

  it('deve tratar erro de rede', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const request = createRequest()
    const response = await GET(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Network error')
  })

  it('deve retornar conversa sem interacoes', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Silva',
          interacoes: [],
        }),
    })

    const request = createRequest()
    const response = await GET(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.interacoes).toHaveLength(0)
  })
})
