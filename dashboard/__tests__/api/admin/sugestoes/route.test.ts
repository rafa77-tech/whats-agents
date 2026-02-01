/**
 * Testes para GET/POST /api/admin/sugestoes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, POST } from '@/app/api/admin/sugestoes/route'
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

function createGetRequest(searchParams: string = '') {
  const url = `http://localhost:3000/api/admin/sugestoes${searchParams ? `?${searchParams}` : ''}`
  return new NextRequest(url, { method: 'GET' })
}

function createPostRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/admin/sugestoes', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  })
}

// =============================================================================
// GET /api/admin/sugestoes
// =============================================================================

describe('GET /api/admin/sugestoes', () => {
  it('deve retornar lista de sugestoes', async () => {
    const mockData = {
      sugestoes: [
        {
          id: 'sug1',
          tipo: 'tom',
          descricao: 'Usar tom mais informal',
          status: 'pending',
          criada_em: '2024-01-15T10:00:00Z',
        },
      ],
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockData),
    })

    const request = createGetRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.sugestoes).toHaveLength(1)
    expect(data.sugestoes[0].tipo).toBe('tom')
  })

  it('deve passar filtro de status para backend', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sugestoes: [] }),
    })

    const request = createGetRequest('status=pending')
    await GET(request)

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('status=pending')
  })

  it('deve incluir header de autorizacao', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ sugestoes: [] }),
    })

    const request = createGetRequest()
    await GET(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    expect((calledOptions.headers as Record<string, string>).Authorization).toContain('Bearer')
  })

  it('deve retornar erro 500 quando backend falha', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Erro interno' }),
    })

    const request = createGetRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Erro interno')
  })

  it('deve tratar erro de rede', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const request = createGetRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Network error')
  })
})

// =============================================================================
// POST /api/admin/sugestoes
// =============================================================================

describe('POST /api/admin/sugestoes', () => {
  const validBody = {
    tipo: 'tom',
    descricao: 'Usar tom mais informal nas respostas',
    exemplos: 'Exemplo: Em vez de "Prezado", usar "Oi"',
  }

  it('deve criar sugestao com sucesso', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug1', ...validBody, status: 'pending' }),
    })

    const request = createPostRequest(validBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.id).toBe('sug1')
    expect(data.status).toBe('pending')
  })

  it('deve enviar body correto para backend', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug1' }),
    })

    const request = createPostRequest(validBody)
    await POST(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    const sentBody = JSON.parse(calledOptions.body as string)

    expect(sentBody.tipo).toBe('tom')
    expect(sentBody.descricao).toBe(validBody.descricao)
    expect(sentBody.exemplos).toBe(validBody.exemplos)
  })

  it('deve aceitar sugestao sem exemplos', async () => {
    const bodyWithoutExamples = {
      tipo: 'resposta',
      descricao: 'Melhorar formato de resposta',
    }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug1' }),
    })

    const request = createPostRequest(bodyWithoutExamples)
    const response = await POST(request)

    expect(response.status).toBe(200)
  })

  it('deve incluir headers corretos', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug1' }),
    })

    const request = createPostRequest(validBody)
    await POST(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    const headers = calledOptions.headers as Record<string, string>

    expect(headers['Content-Type']).toBe('application/json')
    expect(headers.Authorization).toContain('Bearer')
  })

  it('deve retornar erro 500 quando backend falha', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Tipo invalido' }),
    })

    const request = createPostRequest(validBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Tipo invalido')
  })

  it('deve tratar erro de rede', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const request = createPostRequest(validBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Network error')
  })

  it('deve usar metodo POST', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug1' }),
    })

    const request = createPostRequest(validBody)
    await POST(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    expect(calledOptions.method).toBe('POST')
  })
})
