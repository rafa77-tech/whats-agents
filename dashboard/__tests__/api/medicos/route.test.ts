/**
 * Testes para GET /api/medicos
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/medicos/route'
import { NextRequest } from 'next/server'

// Build a self-referencing chainable mock object
const mockRange = vi.fn()
const mockOrder = vi.fn(() => ({ range: mockRange }))
const mockOr = vi.fn()
const mockEq = vi.fn()
const mockIlike = vi.fn()
const mockIs = vi.fn()
const mockSelect = vi.fn()
const mockFrom = vi.fn()

// Each chainable method returns all possible next methods
const chainable = {
  order: mockOrder,
  eq: mockEq,
  ilike: mockIlike,
  or: mockOr,
  is: mockIs,
}

mockFrom.mockReturnValue({ select: mockSelect })
mockSelect.mockReturnValue({ is: mockIs })
mockIs.mockReturnValue(chainable)
mockEq.mockReturnValue(chainable)
mockIlike.mockReturnValue(chainable)
mockOr.mockReturnValue(chainable)

const mockSupabase = { from: mockFrom }

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/medicos?${searchParams}`
  return new NextRequest(url)
}

function mockQueryResult(
  data: Record<string, unknown>[] | null,
  count: number | null,
  error: unknown = null
) {
  mockRange.mockResolvedValue({ data, error, count })
}

describe('GET /api/medicos', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Re-setup chain after clearAllMocks
    mockFrom.mockReturnValue({ select: mockSelect })
    mockSelect.mockReturnValue({ is: mockIs })
    mockIs.mockReturnValue(chainable)
    mockEq.mockReturnValue(chainable)
    mockIlike.mockReturnValue(chainable)
    mockOr.mockReturnValue(chainable)
    mockOrder.mockReturnValue({ range: mockRange })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista paginada de medicos', async () => {
    const clientes = [
      {
        id: '1',
        primeiro_nome: 'Carlos',
        sobrenome: 'Silva',
        telefone: '11999990001',
        especialidade: 'Cardiologia',
        cidade: 'São Paulo',
        stage_jornada: 'lead',
        opt_out: false,
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: '2',
        primeiro_nome: 'Ana',
        sobrenome: 'Costa',
        telefone: '11999990002',
        especialidade: 'Pediatria',
        cidade: 'Rio de Janeiro',
        stage_jornada: 'ativo',
        opt_out: false,
        created_at: '2026-01-02T00:00:00Z',
      },
    ]
    mockQueryResult(clientes, 2)

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.data).toHaveLength(2)
    expect(body.total).toBe(2)
    expect(body.pages).toBe(1)
    expect(body.data[0].nome).toBe('Carlos Silva')
    expect(body.data[1].nome).toBe('Ana Costa')
    expect(mockFrom).toHaveBeenCalledWith('clientes')
    expect(mockIs).toHaveBeenCalledWith('deleted_at', null)
  })

  it('deve filtrar por stage_jornada', async () => {
    mockQueryResult([], 0)

    const request = createRequest({ stage_jornada: 'lead' })
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('stage_jornada', 'lead')
  })

  it('deve filtrar por especialidade com ilike', async () => {
    mockQueryResult([], 0)

    const request = createRequest({ especialidade: 'Cardio' })
    await GET(request)

    expect(mockIlike).toHaveBeenCalledWith('especialidade', '%Cardio%')
  })

  it('deve filtrar por opt_out true', async () => {
    mockQueryResult([], 0)

    const request = createRequest({ opt_out: 'true' })
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('opt_out', true)
  })

  it('deve filtrar por opt_out false', async () => {
    mockQueryResult([], 0)

    const request = createRequest({ opt_out: 'false' })
    await GET(request)

    expect(mockEq).toHaveBeenCalledWith('opt_out', false)
  })

  it('deve aplicar filtro de search com or', async () => {
    mockQueryResult([], 0)

    const request = createRequest({ search: 'Carlos' })
    await GET(request)

    expect(mockOr).toHaveBeenCalledWith(
      'primeiro_nome.ilike.%Carlos%,sobrenome.ilike.%Carlos%,telefone.ilike.%Carlos%,crm.ilike.%Carlos%'
    )
  })

  it('deve calcular paginacao corretamente', async () => {
    mockQueryResult([], 50)

    const request = createRequest({ page: '2', per_page: '10' })
    const response = await GET(request)
    const body = await response.json()

    expect(body.total).toBe(50)
    expect(body.pages).toBe(5)
    // page 2, per_page 10 => from=10, to=19
    expect(mockRange).toHaveBeenCalledWith(10, 19)
  })

  it('deve usar paginacao padrao (page=1, per_page=20)', async () => {
    mockQueryResult([], 0)

    const request = createRequest()
    await GET(request)

    // page 1, per_page 20 => from=0, to=19
    expect(mockRange).toHaveBeenCalledWith(0, 19)
  })

  it('deve retornar contagens zero quando resultado vazio', async () => {
    mockQueryResult([], 0)

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.data).toEqual([])
    expect(body.total).toBe(0)
    expect(body.pages).toBe(0)
  })

  it('deve retornar fallback gracioso quando supabase retorna erro', async () => {
    mockRange.mockResolvedValue({
      data: null,
      error: { message: 'Database error' },
      count: null,
    })
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body).toEqual({ data: [], total: 0, pages: 0 })

    consoleSpy.mockRestore()
  })

  it('deve transformar primeiro_nome + sobrenome em nome', async () => {
    const clientes = [
      {
        id: '1',
        primeiro_nome: 'Maria',
        sobrenome: 'Santos',
        telefone: '11999990001',
        especialidade: null,
        cidade: null,
        stage_jornada: null,
        opt_out: false,
        created_at: '2026-01-01T00:00:00Z',
      },
    ]
    mockQueryResult(clientes, 1)

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    expect(body.data[0].nome).toBe('Maria Santos')
    // Should not expose primeiro_nome or sobrenome
    expect(body.data[0].primeiro_nome).toBeUndefined()
    expect(body.data[0].sobrenome).toBeUndefined()
  })

  it('deve usar apenas primeiro_nome quando sobrenome e null', async () => {
    const clientes = [
      {
        id: '1',
        primeiro_nome: 'João',
        sobrenome: null,
        telefone: '11999990001',
        especialidade: null,
        cidade: null,
        stage_jornada: null,
        opt_out: false,
        created_at: '2026-01-01T00:00:00Z',
      },
    ]
    mockQueryResult(clientes, 1)

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    expect(body.data[0].nome).toBe('João')
  })

  it('deve retornar "Sem nome" quando primeiro_nome e sobrenome sao null', async () => {
    const clientes = [
      {
        id: '1',
        primeiro_nome: null,
        sobrenome: null,
        telefone: '11999990001',
        especialidade: null,
        cidade: null,
        stage_jornada: null,
        opt_out: false,
        created_at: '2026-01-01T00:00:00Z',
      },
    ]
    mockQueryResult(clientes, 1)

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    expect(body.data[0].nome).toBe('Sem nome')
  })

  it('deve retornar "Sem nome" quando primeiro_nome e sobrenome sao strings vazias', async () => {
    const clientes = [
      {
        id: '1',
        primeiro_nome: '',
        sobrenome: '',
        telefone: '11999990001',
        especialidade: null,
        cidade: null,
        stage_jornada: null,
        opt_out: false,
        created_at: '2026-01-01T00:00:00Z',
      },
    ]
    mockQueryResult(clientes, 1)

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    expect(body.data[0].nome).toBe('Sem nome')
  })

  it('deve ordenar por created_at descending', async () => {
    mockQueryResult([], 0)

    const request = createRequest()
    await GET(request)

    expect(mockOrder).toHaveBeenCalledWith('created_at', { ascending: false })
  })

  it('deve transformar campos opcionais corretamente', async () => {
    const clientes = [
      {
        id: '1',
        primeiro_nome: 'Test',
        sobrenome: 'User',
        telefone: null,
        especialidade: null,
        cidade: null,
        stage_jornada: null,
        opt_out: null,
        created_at: '2026-01-01T00:00:00Z',
      },
    ]
    mockQueryResult(clientes, 1)

    const request = createRequest()
    const response = await GET(request)
    const body = await response.json()

    const medico = body.data[0]
    expect(medico.telefone).toBe('')
    expect(medico.especialidade).toBeUndefined()
    expect(medico.cidade).toBeUndefined()
    expect(medico.stage_jornada).toBeUndefined()
    expect(medico.opt_out).toBe(false)
  })
})
