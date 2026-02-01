/**
 * Testes para GET e POST /api/diretrizes
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, POST } from '@/app/api/diretrizes/route'
import { NextRequest } from 'next/server'

// =============================================================================
// Mocks
// =============================================================================

const mockSelect = vi.fn()
const mockIn = vi.fn()
const mockOrder = vi.fn()
const mockInsert = vi.fn()
const mockSingle = vi.fn()
const mockFrom = vi.fn()
const mockGetUser = vi.fn()

const mockSupabase = {
  from: mockFrom,
  auth: {
    getUser: mockGetUser,
  },
}

vi.mock('@/lib/supabase/server', () => ({
  createClient: () => mockSupabase,
}))

function createRequest(method: string, url: string, body?: unknown) {
  const requestUrl = `http://localhost:3000${url}`
  if (body) {
    return new NextRequest(requestUrl, {
      method,
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
  }
  return new NextRequest(requestUrl, { method })
}

// =============================================================================
// GET /api/diretrizes
// =============================================================================

describe('GET /api/diretrizes', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup chain for select
    mockFrom.mockReturnValue({ select: mockSelect })
    mockSelect.mockReturnValue({ in: mockIn })
    mockIn.mockReturnValue({ order: mockOrder })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista de diretrizes', async () => {
    const mockDiretrizes = [
      {
        id: '1',
        tipo: 'margem_negociacao',
        escopo: 'global',
        conteudo: { valor_maximo: 3000 },
        status: 'ativa',
      },
    ]

    mockOrder.mockResolvedValue({ data: mockDiretrizes, error: null })

    const request = createRequest('GET', '/api/diretrizes?status=ativa')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toHaveLength(1)
    expect(data[0].tipo).toBe('margem_negociacao')
  })

  it('deve filtrar por status', async () => {
    mockOrder.mockResolvedValue({ data: [], error: null })

    const request = createRequest('GET', '/api/diretrizes?status=expirada,cancelada')
    await GET(request)

    expect(mockIn).toHaveBeenCalledWith('status', ['expirada', 'cancelada'])
  })

  it('deve usar status ativa como default', async () => {
    mockOrder.mockResolvedValue({ data: [], error: null })

    const request = createRequest('GET', '/api/diretrizes')
    await GET(request)

    expect(mockIn).toHaveBeenCalledWith('status', ['ativa'])
  })

  it('deve fazer select com joins', async () => {
    mockOrder.mockResolvedValue({ data: [], error: null })

    const request = createRequest('GET', '/api/diretrizes')
    await GET(request)

    expect(mockFrom).toHaveBeenCalledWith('diretrizes_contextuais')
    expect(mockSelect).toHaveBeenCalled()
    const selectArg = mockSelect.mock.calls[0]?.[0] as string
    expect(selectArg).toContain('vagas')
    expect(selectArg).toContain('clientes')
    expect(selectArg).toContain('hospitais')
    expect(selectArg).toContain('especialidades')
  })

  it('deve ordenar por created_at desc', async () => {
    mockOrder.mockResolvedValue({ data: [], error: null })

    const request = createRequest('GET', '/api/diretrizes')
    await GET(request)

    expect(mockOrder).toHaveBeenCalledWith('created_at', { ascending: false })
  })

  it('deve retornar erro 500 em caso de erro no banco', async () => {
    mockOrder.mockResolvedValue({ data: null, error: { message: 'DB error' } })

    const request = createRequest('GET', '/api/diretrizes')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao buscar diretrizes')
  })

  it('deve retornar array vazio se data for null', async () => {
    mockOrder.mockResolvedValue({ data: null, error: null })

    const request = createRequest('GET', '/api/diretrizes')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })
})

// =============================================================================
// POST /api/diretrizes
// =============================================================================

describe('POST /api/diretrizes', () => {
  beforeEach(() => {
    vi.clearAllMocks()

    // Setup chain for insert
    mockFrom.mockImplementation((table: string) => {
      if (table === 'diretrizes_contextuais') {
        return { insert: mockInsert }
      }
      if (table === 'audit_log') {
        return { insert: vi.fn().mockResolvedValue({ error: null }) }
      }
      return { insert: vi.fn() }
    })
    mockInsert.mockReturnValue({ select: vi.fn().mockReturnValue({ single: mockSingle }) })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve criar diretriz com sucesso', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com', id: '1' } },
    })

    const createdDiretriz = {
      id: '1',
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
      criado_por: 'admin@test.com',
      status: 'ativa',
    }

    mockSingle.mockResolvedValue({ data: createdDiretriz, error: null })

    const request = createRequest('POST', '/api/diretrizes', {
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
    })

    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.tipo).toBe('margem_negociacao')
  })

  it('deve retornar 401 se nao autenticado', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } })

    const request = createRequest('POST', '/api/diretrizes', {
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
    })

    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.detail).toBe('Nao autorizado')
  })

  it('deve adicionar criado_por do usuario', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com', id: '1' } },
    })

    mockSingle.mockResolvedValue({
      data: { id: '1', criado_por: 'admin@test.com' },
      error: null,
    })

    const request = createRequest('POST', '/api/diretrizes', {
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
    })

    await POST(request)

    const insertArg = mockInsert.mock.calls[0]?.[0] as Record<string, unknown>
    expect(insertArg.criado_por).toBe('admin@test.com')
    expect(insertArg.status).toBe('ativa')
  })

  it('deve retornar erro 500 em caso de erro no banco', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com', id: '1' } },
    })

    mockSingle.mockResolvedValue({ data: null, error: { message: 'DB error' } })

    const request = createRequest('POST', '/api/diretrizes', {
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
    })

    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao criar diretriz')
  })
})
