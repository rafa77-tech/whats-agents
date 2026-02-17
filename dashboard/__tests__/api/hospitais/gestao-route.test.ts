/**
 * Testes para GET /api/hospitais/gestao
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/hospitais/gestao/route'
import { NextRequest } from 'next/server'

const mockListarHospitaisGestao = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  listarHospitaisGestao: (...args: unknown[]) => mockListarHospitaisGestao(...args),
}))

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => ({}),
}))

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/hospitais/gestao?${searchParams}`
  return new NextRequest(url)
}

describe('GET /api/hospitais/gestao', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista paginada de hospitais', async () => {
    const mockResponse = {
      data: [
        {
          id: 'h1',
          nome: 'Hospital A',
          cidade: 'SP',
          vagas_count: 5,
          aliases_count: 2,
          precisa_revisao: false,
          criado_automaticamente: false,
        },
      ],
      total: 1,
      pages: 1,
    }
    mockListarHospitaisGestao.mockResolvedValue(mockResponse)

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.data).toHaveLength(1)
    expect(data.total).toBe(1)
    expect(mockListarHospitaisGestao).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ page: 1, perPage: 20, status: 'todos' })
    )
  })

  it('deve passar parametros de busca e filtro', async () => {
    mockListarHospitaisGestao.mockResolvedValue({ data: [], total: 0, pages: 0 })

    const request = createRequest({ search: 'teste', status: 'pendentes', page: '2' })
    await GET(request)

    expect(mockListarHospitaisGestao).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({ search: 'teste', status: 'pendentes', page: 2 })
    )
  })

  it('deve retornar 500 em caso de erro', async () => {
    mockListarHospitaisGestao.mockRejectedValue(new Error('DB error'))

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('DB error')
  })
})
