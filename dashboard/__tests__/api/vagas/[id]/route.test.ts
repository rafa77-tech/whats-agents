/**
 * Testes para GET/PATCH/DELETE /api/vagas/[id]
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, PATCH, DELETE } from '@/app/api/vagas/[id]/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient
const mockEq = vi.fn()
const mockUpdate = vi.fn()
const mockDelete = vi.fn()
const mockSelect = vi.fn()
const mockFrom = vi.fn()

const mockSupabase = {
  from: mockFrom,
}

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

function createRequest(method: string = 'GET', body?: Record<string, unknown>) {
  const url = 'http://localhost:3000/api/vagas/123'
  const init = { method } as { method: string; body?: string; headers?: Record<string, string> }
  if (body) {
    init.body = JSON.stringify(body)
    init.headers = { 'Content-Type': 'application/json' }
  }
  return new NextRequest(url, init)
}

function createParams(id: string = '123') {
  return { params: Promise.resolve({ id }) }
}

describe('GET /api/vagas/[id]', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFrom.mockReturnValue({
      select: mockSelect,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns shift details', async () => {
    const mockVaga = {
      id: 'vaga1',
      data: '2024-01-15',
      hora_inicio: '08:00',
      hora_fim: '18:00',
      valor: 1500,
      status: 'aberta',
      created_at: '2024-01-10T10:00:00Z',
      updated_at: '2024-01-11T10:00:00Z',
      hospital_id: 'h1',
      especialidade_id: 'e1',
      setor_id: 's1',
      cliente_id: null,
      hospitais: { id: 'h1', nome: 'Hospital ABC' },
      especialidades: { id: 'e1', nome: 'Cardiologia' },
      setores: { id: 's1', nome: 'UTI' },
      clientes: null,
    }

    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: mockVaga,
          error: null,
        }),
      }),
    })

    const request = createRequest()
    const response = await GET(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.id).toBe('vaga1')
    expect(data.hospital).toBe('Hospital ABC')
    expect(data.especialidade).toBe('Cardiologia')
    expect(data.setor).toBe('UTI')
  })

  it('returns 404 for non-existent shift', async () => {
    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: null,
          error: { code: 'PGRST116', message: 'Not found' },
        }),
      }),
    })

    const request = createRequest()
    const response = await GET(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(404)
    expect(data.error).toBe('Vaga nao encontrada')
  })

  it('handles database errors', async () => {
    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: null,
          error: { code: 'OTHER', message: 'Database error' },
        }),
      }),
    })

    const request = createRequest()
    const response = await GET(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Erro ao buscar vaga')
  })

  it('transforms cliente name correctly', async () => {
    const mockVaga = {
      id: 'vaga1',
      data: '2024-01-15',
      hora_inicio: '08:00',
      hora_fim: '18:00',
      valor: 1500,
      status: 'reservada',
      created_at: '2024-01-10T10:00:00Z',
      updated_at: null,
      hospital_id: 'h1',
      especialidade_id: 'e1',
      setor_id: null,
      cliente_id: 'c1',
      hospitais: { id: 'h1', nome: 'Hospital ABC' },
      especialidades: { id: 'e1', nome: 'Cardiologia' },
      setores: null,
      clientes: { id: 'c1', primeiro_nome: 'Carlos', sobrenome: 'Silva' },
    }

    mockSelect.mockReturnValue({
      eq: vi.fn().mockReturnValue({
        single: vi.fn().mockResolvedValue({
          data: mockVaga,
          error: null,
        }),
      }),
    })

    const request = createRequest()
    const response = await GET(request, createParams())
    const data = await response.json()

    expect(data.cliente_nome).toBe('Carlos Silva')
    expect(data.setor).toBeNull()
  })
})

describe('PATCH /api/vagas/[id]', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFrom.mockReturnValue({
      update: mockUpdate,
    })
    mockUpdate.mockReturnValue({
      eq: mockEq,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('updates shift', async () => {
    mockEq.mockResolvedValue({ error: null })

    const request = createRequest('PATCH', { status: 'confirmada' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
  })

  it('assigns doctor and changes status to reservada', async () => {
    mockEq.mockResolvedValue({ error: null })

    const clienteId = '550e8400-e29b-41d4-a716-446655440000'
    const request = createRequest('PATCH', { cliente_id: clienteId })
    const response = await PATCH(request, createParams())

    expect(response.status).toBe(200)
    expect(mockUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        cliente_id: clienteId,
        status: 'reservada',
      })
    )
  })

  it('validates body with Zod - invalid status returns 400', async () => {
    const request = createRequest('PATCH', { status: 'invalid' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.error).toBe('Dados invalidos')
  })

  it('validates body with Zod - invalid UUID returns 400', async () => {
    const request = createRequest('PATCH', { cliente_id: 'not-a-uuid' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.error).toBe('Dados invalidos')
  })

  it('allows null cliente_id', async () => {
    mockEq.mockResolvedValue({ error: null })

    const request = createRequest('PATCH', { cliente_id: null })
    const response = await PATCH(request, createParams())

    expect(response.status).toBe(200)
    expect(mockUpdate).toHaveBeenCalledWith(
      expect.objectContaining({
        cliente_id: null,
      })
    )
  })

  it('updates criticidade', async () => {
    mockEq.mockResolvedValue({ error: null })

    const request = createRequest('PATCH', { criticidade: 'urgente' })
    const response = await PATCH(request, createParams())

    expect(response.status).toBe(200)
    expect(mockUpdate).toHaveBeenCalledWith(expect.objectContaining({ criticidade: 'urgente' }))
  })

  it('rejects invalid criticidade', async () => {
    const request = createRequest('PATCH', { criticidade: 'invalida' })
    const response = await PATCH(request, createParams())

    expect(response.status).toBe(400)
  })

  it('handles database errors', async () => {
    mockEq.mockResolvedValue({ error: { message: 'Database error' } })

    const request = createRequest('PATCH', { status: 'confirmada' })
    const response = await PATCH(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Erro ao atualizar vaga')
  })
})

describe('DELETE /api/vagas/[id]', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockFrom.mockReturnValue({
      delete: mockDelete,
    })
    mockDelete.mockReturnValue({
      eq: mockEq,
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deletes shift', async () => {
    mockEq.mockResolvedValue({ error: null })

    const request = createRequest('DELETE')
    const response = await DELETE(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockDelete).toHaveBeenCalled()
    expect(mockEq).toHaveBeenCalledWith('id', '123')
  })

  it('handles errors', async () => {
    mockEq.mockResolvedValue({ error: { message: 'Database error' } })

    const request = createRequest('DELETE')
    const response = await DELETE(request, createParams())
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.error).toBe('Erro ao deletar vaga')
  })
})
