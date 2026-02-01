/**
 * Testes para GET /api/hospitais
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/hospitais/route'
import { NextRequest } from 'next/server'

// Mock lib/hospitais
const mockListarHospitais = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  listarHospitais: (...args: unknown[]) => mockListarHospitais(...args),
}))

// Mock createClient
vi.mock('@/lib/supabase/server', () => ({
  createClient: () => Promise.resolve({}),
}))

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/hospitais?${searchParams}`
  return new NextRequest(url)
}

describe('GET /api/hospitais', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista de hospitais', async () => {
    const mockData = [
      { id: 'h1', nome: 'Hospital A', cidade: 'SP', vagas_abertas: 5 },
      { id: 'h2', nome: 'Hospital B', cidade: 'RJ', vagas_abertas: 3 },
    ]
    mockListarHospitais.mockResolvedValue(mockData)

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockData)
    expect(mockListarHospitais).toHaveBeenCalledWith(expect.anything(), {
      excluirBloqueados: false,
    })
  })

  it('deve excluir bloqueados quando parametro for true', async () => {
    const mockData = [{ id: 'h2', nome: 'Hospital B', cidade: 'RJ', vagas_abertas: 3 }]
    mockListarHospitais.mockResolvedValue(mockData)

    const request = createRequest({ excluir_bloqueados: 'true' })
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toHaveLength(1)
    expect(mockListarHospitais).toHaveBeenCalledWith(expect.anything(), { excluirBloqueados: true })
  })

  it('deve retornar array vazio quando nao ha hospitais', async () => {
    mockListarHospitais.mockResolvedValue([])

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })

  it('deve retornar erro 500 quando repository lanca erro', async () => {
    mockListarHospitais.mockRejectedValue(new Error('DB Error'))

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('DB Error')
  })

  it('deve retornar mensagem generica quando erro nao tem message', async () => {
    mockListarHospitais.mockRejectedValue('Unknown error')

    const request = createRequest()
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro interno do servidor')
  })

  it('deve nao excluir bloqueados quando parametro for false', async () => {
    mockListarHospitais.mockResolvedValue([])

    const request = createRequest({ excluir_bloqueados: 'false' })
    await GET(request)

    expect(mockListarHospitais).toHaveBeenCalledWith(expect.anything(), {
      excluirBloqueados: false,
    })
  })
})
