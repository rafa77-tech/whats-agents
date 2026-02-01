/**
 * Testes para PATCH /api/diretrizes/[id]
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { PATCH } from '@/app/api/diretrizes/[id]/route'
import { NextRequest } from 'next/server'

// =============================================================================
// Mocks
// =============================================================================

const mockSelect = vi.fn()
const mockUpdate = vi.fn()
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

function createRequest(url: string, body: unknown) {
  return new NextRequest(`http://localhost:3000${url}`, {
    method: 'PATCH',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  })
}

// =============================================================================
// PATCH /api/diretrizes/[id]
// =============================================================================

describe('PATCH /api/diretrizes/[id]', () => {
  const mockDiretriz = {
    id: '123',
    tipo: 'margem_negociacao',
    escopo: 'global',
    conteudo: { valor_maximo: 3000 },
    status: 'ativa',
  }

  beforeEach(() => {
    vi.clearAllMocks()

    // Setup default chain
    mockFrom.mockImplementation((table: string) => {
      if (table === 'diretrizes_contextuais') {
        return {
          select: mockSelect,
          update: mockUpdate,
        }
      }
      if (table === 'audit_log') {
        return { insert: vi.fn().mockResolvedValue({ error: null }) }
      }
      return {}
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve cancelar diretriz com sucesso', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com', id: '1' } },
    })

    // Mock para buscar diretriz
    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockDiretriz, error: null }),
      }),
    })

    // Mock para update
    mockUpdate.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({
            data: { ...mockDiretriz, status: 'cancelada' },
            error: null,
          }),
        }),
      }),
    })

    const request = createRequest('/api/diretrizes/123', { status: 'cancelada' })
    const response = await PATCH(request, { params: Promise.resolve({ id: '123' }) })
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.status).toBe('cancelada')
  })

  it('deve retornar 401 se nao autenticado', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } })

    const request = createRequest('/api/diretrizes/123', { status: 'cancelada' })
    const response = await PATCH(request, { params: Promise.resolve({ id: '123' }) })
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.detail).toBe('Nao autorizado')
  })

  it('deve retornar 404 se diretriz nao encontrada', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com', id: '1' } },
    })

    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: null, error: { code: 'PGRST116' } }),
      }),
    })

    const request = createRequest('/api/diretrizes/999', { status: 'cancelada' })
    const response = await PATCH(request, { params: Promise.resolve({ id: '999' }) })
    const data = await response.json()

    expect(response.status).toBe(404)
    expect(data.detail).toBe('Diretriz nao encontrada')
  })

  it('deve adicionar cancelado_por e cancelado_em', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com', id: '1' } },
    })

    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockDiretriz, error: null }),
      }),
    })

    const updateMock = vi.fn().mockReturnValue({
      select: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: { ...mockDiretriz, status: 'cancelada' },
          error: null,
        }),
      }),
    })

    mockUpdate.mockReturnValue({
      eq: updateMock,
    })

    const request = createRequest('/api/diretrizes/123', { status: 'cancelada' })
    await PATCH(request, { params: Promise.resolve({ id: '123' }) })

    const updateArg = mockUpdate.mock.calls[0]?.[0] as Record<string, unknown>
    expect(updateArg.status).toBe('cancelada')
    expect(updateArg.cancelado_por).toBe('admin@test.com')
    expect(updateArg.cancelado_em).toBeDefined()
  })

  it('deve retornar erro 500 em caso de erro no update', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com', id: '1' } },
    })

    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({ data: mockDiretriz, error: null }),
      }),
    })

    mockUpdate.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        select: vi.fn().mockReturnValue({
          single: vi.fn().mockResolvedValue({ data: null, error: { message: 'DB error' } }),
        }),
      }),
    })

    const request = createRequest('/api/diretrizes/123', { status: 'cancelada' })
    const response = await PATCH(request, { params: Promise.resolve({ id: '123' }) })
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao atualizar diretriz')
  })
})
