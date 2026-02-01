/**
 * Testes para GET /api/ajuda
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { NextRequest } from 'next/server'

// Mock Supabase client
const mockSelect = vi.fn()
const mockOrder = vi.fn()
const mockLimit = vi.fn()
const mockIn = vi.fn()

vi.mock('@/lib/supabase/server', () => ({
  createClient: vi.fn(() =>
    Promise.resolve({
      from: vi.fn(() => ({
        select: mockSelect.mockReturnThis(),
        order: mockOrder.mockReturnThis(),
        limit: mockLimit.mockReturnThis(),
        in: mockIn,
      })),
    })
  ),
}))

describe('GET /api/ajuda', () => {
  beforeEach(() => {
    vi.resetModules()
    mockSelect.mockReset()
    mockOrder.mockReset()
    mockLimit.mockReset()
    mockIn.mockReset()
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  it('deve retornar lista de pedidos de ajuda', async () => {
    const mockPedidos = [
      {
        id: '1',
        pergunta_original: 'Pergunta 1',
        status: 'pendente',
        criado_em: '2026-01-30T10:00:00Z',
        clientes: { nome: 'Dr. A', telefone: '11111' },
      },
    ]

    mockLimit.mockResolvedValueOnce({ data: mockPedidos, error: null })

    const { GET } = await import('@/app/api/ajuda/route')
    const request = new NextRequest('http://localhost/api/ajuda')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockPedidos)
  })

  it('deve filtrar por status quando parametro fornecido', async () => {
    mockIn.mockResolvedValueOnce({ data: [], error: null })

    const { GET } = await import('@/app/api/ajuda/route')
    const request = new NextRequest('http://localhost/api/ajuda?status=pendente,timeout')
    await GET(request)

    expect(mockIn).toHaveBeenCalledWith('status', ['pendente', 'timeout'])
  })

  it('deve retornar todos quando status vazio', async () => {
    mockLimit.mockResolvedValueOnce({ data: [], error: null })

    const { GET } = await import('@/app/api/ajuda/route')
    const request = new NextRequest('http://localhost/api/ajuda')
    await GET(request)

    expect(mockIn).not.toHaveBeenCalled()
  })

  it('deve retornar erro 500 quando query falha', async () => {
    mockLimit.mockResolvedValueOnce({ data: null, error: { message: 'DB Error' } })

    const { GET } = await import('@/app/api/ajuda/route')
    const request = new NextRequest('http://localhost/api/ajuda')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toContain('Erro')
  })

  it('deve retornar array vazio quando nao ha dados', async () => {
    mockLimit.mockResolvedValueOnce({ data: null, error: null })

    const { GET } = await import('@/app/api/ajuda/route')
    const request = new NextRequest('http://localhost/api/ajuda')
    const response = await GET(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })

  it('deve ordenar por criado_em descendente', async () => {
    mockLimit.mockResolvedValueOnce({ data: [], error: null })

    const { GET } = await import('@/app/api/ajuda/route')
    const request = new NextRequest('http://localhost/api/ajuda')
    await GET(request)

    expect(mockOrder).toHaveBeenCalledWith('criado_em', { ascending: false })
  })

  it('deve limitar a 50 resultados', async () => {
    mockLimit.mockResolvedValueOnce({ data: [], error: null })

    const { GET } = await import('@/app/api/ajuda/route')
    const request = new NextRequest('http://localhost/api/ajuda')
    await GET(request)

    expect(mockLimit).toHaveBeenCalledWith(50)
  })
})
