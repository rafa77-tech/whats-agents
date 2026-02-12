/**
 * Testes para POST /api/ajuda/[id]/responder
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { NextRequest } from 'next/server'

// Mock Supabase client
const mockGetUser = vi.fn()
const mockSelect = vi.fn()
const mockEq = vi.fn()
const mockSingle = vi.fn()
const mockUpdate = vi.fn()
const mockInsert = vi.fn()

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() =>
    Promise.resolve({
      auth: {
        getUser: mockGetUser,
      },
      from: vi.fn((table) => {
        if (table === 'audit_log') {
          return { insert: mockInsert }
        }
        return {
          select: mockSelect.mockReturnThis(),
          eq: mockEq.mockReturnThis(),
          single: mockSingle,
          update: mockUpdate.mockReturnThis(),
        }
      }),
    })
  ),
}))

describe('POST /api/ajuda/[id]/responder', () => {
  const originalFetch = global.fetch
  let mockFetch: ReturnType<typeof vi.fn>

  function createRequest(body: object): NextRequest {
    return new NextRequest('http://localhost/api/ajuda/123/responder', {
      method: 'POST',
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  beforeEach(() => {
    vi.resetModules()
    mockFetch = vi.fn()
    global.fetch = mockFetch as unknown as typeof fetch

    // Reset mocks
    mockGetUser.mockReset()
    mockSelect.mockReset()
    mockEq.mockReset()
    mockSingle.mockReset()
    mockUpdate.mockReset()
    mockInsert.mockReset()
  })

  afterEach(() => {
    global.fetch = originalFetch
    vi.clearAllMocks()
  })

  it('deve retornar 401 quando usuario nao autenticado', async () => {
    mockGetUser.mockResolvedValueOnce({ data: { user: null } })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    const response = await POST(createRequest({ resposta: 'Resposta teste' }), {
      params: Promise.resolve({ id: '123' }),
    })
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.detail).toContain('Nao autorizado')
  })

  it('deve retornar 400 quando resposta vazia', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    const response = await POST(createRequest({ resposta: '' }), {
      params: Promise.resolve({ id: '123' }),
    })
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toContain('obrigatoria')
  })

  it('deve retornar 400 quando resposta e apenas espacos', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    const response = await POST(createRequest({ resposta: '   ' }), {
      params: Promise.resolve({ id: '123' }),
    })
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toContain('obrigatoria')
  })

  it('deve retornar 404 quando pedido nao encontrado', async () => {
    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle.mockResolvedValueOnce({ data: null, error: { code: 'PGRST116' } })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    const response = await POST(createRequest({ resposta: 'Resposta teste' }), {
      params: Promise.resolve({ id: '123' }),
    })
    const data = await response.json()

    expect(response.status).toBe(404)
    expect(data.detail).toContain('nao encontrado')
  })

  it('deve responder pedido quando valido', async () => {
    const mockPedido = { id: '123', conversa_id: 'conv-1', status: 'pendente' }
    const mockUpdated = {
      id: '123',
      status: 'respondido',
      resposta: 'Resposta teste',
      respondido_por: 'user@test.com',
    }

    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle
      .mockResolvedValueOnce({ data: mockPedido, error: null }) // buscar pedido
      .mockResolvedValueOnce({ data: mockUpdated, error: null }) // update
    mockInsert.mockResolvedValueOnce({ error: null })
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    const response = await POST(createRequest({ resposta: 'Resposta teste' }), {
      params: Promise.resolve({ id: '123' }),
    })
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.status).toBe('respondido')
    expect(data.resposta).toBe('Resposta teste')
  })

  it('deve chamar API para retomar conversa', async () => {
    const mockPedido = { id: '123', conversa_id: 'conv-1', status: 'pendente' }
    const mockUpdated = { id: '123', status: 'respondido' }

    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle
      .mockResolvedValueOnce({ data: mockPedido, error: null })
      .mockResolvedValueOnce({ data: mockUpdated, error: null })
    mockInsert.mockResolvedValueOnce({ error: null })
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    await POST(createRequest({ resposta: 'Resposta teste' }), {
      params: Promise.resolve({ id: '123' }),
    })

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/conversas/conv-1/retomar'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          resposta_gestor: 'Resposta teste',
          pedido_ajuda_id: '123',
        }),
      })
    )
  })

  it('deve registrar audit log', async () => {
    const mockPedido = { id: '123', conversa_id: 'conv-1', status: 'pendente' }
    const mockUpdated = { id: '123', status: 'respondido' }

    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle
      .mockResolvedValueOnce({ data: mockPedido, error: null })
      .mockResolvedValueOnce({ data: mockUpdated, error: null })
    mockInsert.mockResolvedValueOnce({ error: null })
    mockFetch.mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    await POST(createRequest({ resposta: 'Resposta teste' }), {
      params: Promise.resolve({ id: '123' }),
    })

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        action: 'pedido_ajuda_respondido',
        user_email: 'user@test.com',
      })
    )
  })

  it('deve retornar sucesso mesmo se retomar conversa falhar', async () => {
    const mockPedido = { id: '123', conversa_id: 'conv-1', status: 'pendente' }
    const mockUpdated = { id: '123', status: 'respondido' }

    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle
      .mockResolvedValueOnce({ data: mockPedido, error: null })
      .mockResolvedValueOnce({ data: mockUpdated, error: null })
    mockInsert.mockResolvedValueOnce({ error: null })
    mockFetch.mockRejectedValueOnce(new Error('Network error'))

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    const response = await POST(createRequest({ resposta: 'Resposta teste' }), {
      params: Promise.resolve({ id: '123' }),
    })

    // Deve retornar 200 mesmo com erro na API de retomar
    expect(response.status).toBe(200)
  })

  it('deve retornar erro 500 quando update falha', async () => {
    const mockPedido = { id: '123', conversa_id: 'conv-1', status: 'pendente' }

    mockGetUser.mockResolvedValueOnce({
      data: { user: { id: 'user-1', email: 'user@test.com' } },
    })
    mockSingle
      .mockResolvedValueOnce({ data: mockPedido, error: null })
      .mockResolvedValueOnce({ data: null, error: { message: 'Update failed' } })

    const { POST } = await import('@/app/api/ajuda/[id]/responder/route')
    const response = await POST(createRequest({ resposta: 'Resposta teste' }), {
      params: Promise.resolve({ id: '123' }),
    })
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toContain('Erro')
  })
})
