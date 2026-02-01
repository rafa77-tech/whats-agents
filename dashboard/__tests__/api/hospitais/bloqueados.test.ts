/**
 * Testes para GET /api/hospitais/bloqueados
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/hospitais/bloqueados/route'
import { NextRequest } from 'next/server'

// Mock lib/hospitais
const mockListarHospitaisBloqueados = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  listarHospitaisBloqueados: (...args: unknown[]) => mockListarHospitaisBloqueados(...args),
}))

// Mock createClient
vi.mock('@/lib/supabase/server', () => ({
  createClient: () => Promise.resolve({}),
}))

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/hospitais/bloqueados?${searchParams}`
  return new NextRequest(url)
}

describe('GET /api/hospitais/bloqueados', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista de hospitais bloqueados', async () => {
    const mockData = [
      {
        id: '1',
        hospital_id: 'h1',
        motivo: 'Pagamento atrasado',
        bloqueado_por: 'admin@test.com',
        bloqueado_em: '2024-01-15T10:00:00Z',
        status: 'bloqueado',
        vagas_movidas: 3,
        hospitais: { nome: 'Hospital A', cidade: 'SP' },
      },
    ]
    mockListarHospitaisBloqueados.mockResolvedValue(mockData)

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockData)
    expect(mockListarHospitaisBloqueados).toHaveBeenCalledWith(expect.anything(), {
      incluirHistorico: false,
    })
  })

  it('deve incluir historico quando parametro for true', async () => {
    const mockData = [
      { id: '1', status: 'bloqueado' },
      { id: '2', status: 'desbloqueado' },
    ]
    mockListarHospitaisBloqueados.mockResolvedValue(mockData)

    const request = createRequest({ historico: 'true' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toHaveLength(2)
    expect(mockListarHospitaisBloqueados).toHaveBeenCalledWith(expect.anything(), {
      incluirHistorico: true,
    })
  })

  it('deve retornar array vazio quando nao ha bloqueados', async () => {
    mockListarHospitaisBloqueados.mockResolvedValue([])

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })

  it('deve retornar erro 500 quando repository lanca erro', async () => {
    mockListarHospitaisBloqueados.mockRejectedValue(new Error('DB Error'))

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('DB Error')
  })

  it('deve retornar mensagem generica quando erro nao tem message', async () => {
    mockListarHospitaisBloqueados.mockRejectedValue('Unknown error')

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro interno do servidor')
  })
})
