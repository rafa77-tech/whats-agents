/**
 * Testes para PATCH /api/admin/sugestoes/[id]
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { PATCH } from '@/app/api/admin/sugestoes/[id]/route'
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
  return new NextRequest('http://localhost:3000/api/admin/sugestoes/sug123', {
    method: 'PATCH',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  })
}

function createParams(id: string = 'sug123') {
  return { params: Promise.resolve({ id }) }
}

describe('PATCH /api/admin/sugestoes/[id]', () => {
  it('deve atualizar status para approved', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug123', status: 'approved' }),
    })

    const request = createRequest({ status: 'approved' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.status).toBe('approved')
  })

  it('deve atualizar status para rejected', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug123', status: 'rejected' }),
    })

    const request = createRequest({ status: 'rejected' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.status).toBe('rejected')
  })

  it('deve atualizar status para implemented', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug123', status: 'implemented' }),
    })

    const request = createRequest({ status: 'implemented' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.status).toBe('implemented')
  })

  it('deve chamar backend com ID correto', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug456', status: 'approved' }),
    })

    const request = createRequest({ status: 'approved' })
    await PATCH(request, createParams('sug456'))

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('/admin/sugestoes/sug456')
  })

  it('deve enviar body correto para backend', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug123', status: 'approved' }),
    })

    const request = createRequest({ status: 'approved' })
    await PATCH(request, createParams())

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    const sentBody = JSON.parse(calledOptions.body as string)

    expect(sentBody.status).toBe('approved')
  })

  it('deve incluir headers corretos', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug123', status: 'approved' }),
    })

    const request = createRequest({ status: 'approved' })
    await PATCH(request, createParams())

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    const headers = calledOptions.headers as Record<string, string>

    expect(headers['Content-Type']).toBe('application/json')
    expect(headers.Authorization).toContain('Bearer')
  })

  it('deve usar metodo PATCH', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ id: 'sug123', status: 'approved' }),
    })

    const request = createRequest({ status: 'approved' })
    await PATCH(request, createParams())

    const calledOptions = mockFetch.mock.calls[0]?.[1] as RequestInit
    expect(calledOptions.method).toBe('PATCH')
  })

  it('deve retornar erro 500 quando backend falha', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Sugestao nao encontrada' }),
    })

    const request = createRequest({ status: 'approved' })
    const response = await PATCH(request, createParams('inexistente'))
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Sugestao nao encontrada')
  })

  it('deve tratar erro de rede', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const request = createRequest({ status: 'approved' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Network error')
  })

  it('deve retornar erro quando transicao de status invalida', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Transicao de status invalida' }),
    })

    const request = createRequest({ status: 'implemented' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Transicao de status invalida')
  })
})
