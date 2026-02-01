/**
 * Testes para POST /api/admin/avaliacoes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { POST } from '@/app/api/admin/avaliacoes/route'
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

function createRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/admin/avaliacoes', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('POST /api/admin/avaliacoes', () => {
  const validBody = {
    conversa_id: '550e8400-e29b-41d4-a716-446655440000',
    naturalidade: 4,
    persona: 5,
    objetivo: 4,
    satisfacao: 4,
    observacoes: 'Boa conversa',
  }

  it('deve criar avaliacao com sucesso', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'eval1', ...validBody }),
    })

    const request = createRequest(validBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.id).toBe('eval1')
  })

  it('deve enviar body correto para backend', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'eval1' }),
    })

    const request = createRequest(validBody)
    await POST(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    const sentBody = JSON.parse(calledOptions.body as string)

    expect(sentBody.conversa_id).toBe(validBody.conversa_id)
    expect(sentBody.naturalidade).toBe(4)
    expect(sentBody.persona).toBe(5)
    expect(sentBody.objetivo).toBe(4)
    expect(sentBody.satisfacao).toBe(4)
    expect(sentBody.observacoes).toBe('Boa conversa')
  })

  it('deve incluir headers corretos', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'eval1' }),
    })

    const request = createRequest(validBody)
    await POST(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    const headers = calledOptions.headers as Record<string, string>

    expect(headers['Content-Type']).toBe('application/json')
    expect(headers.Authorization).toContain('Bearer')
  })

  it('deve retornar erro 500 quando backend falha', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Conversa ja avaliada' }),
    })

    const request = createRequest(validBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Conversa ja avaliada')
  })

  it('deve tratar erro de rede', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const request = createRequest(validBody)
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Network error')
  })

  it('deve aceitar avaliacao sem observacoes', async () => {
    const bodyWithoutObs = { ...validBody, observacoes: '' }

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'eval1' }),
    })

    const request = createRequest(bodyWithoutObs)
    const response = await POST(request)

    expect(response.status).toBe(200)
  })

  it('deve usar metodo POST', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'eval1' }),
    })

    const request = createRequest(validBody)
    await POST(request)

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    expect(calledOptions.method).toBe('POST')
  })
})
