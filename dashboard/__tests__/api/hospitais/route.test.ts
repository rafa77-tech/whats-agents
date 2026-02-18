/**
 * Testes para GET /api/hospitais e POST /api/hospitais
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, POST } from '@/app/api/hospitais/route'
import { NextRequest } from 'next/server'

// Mock lib/hospitais
const mockListarHospitais = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  listarHospitais: (...args: unknown[]) => mockListarHospitais(...args),
}))

// Mock createAdminClient
const mockSingle = vi.fn()
const mockSelectChain = vi.fn(() => ({ single: mockSingle }))
const mockInsert = vi.fn(() => ({ select: mockSelectChain }))
const mockAdminFrom = vi.fn(() => ({ insert: mockInsert }))

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => ({ from: mockAdminFrom }),
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
      apenasRevisados: true,
      limit: 50,
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
    expect(mockListarHospitais).toHaveBeenCalledWith(expect.anything(), {
      excluirBloqueados: true,
      apenasRevisados: true,
      limit: 50,
    })
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
      apenasRevisados: true,
      limit: 50,
    })
  })

  it('deve desabilitar apenasRevisados quando parametro for false', async () => {
    mockListarHospitais.mockResolvedValue([])

    const request = createRequest({ apenas_revisados: 'false' })
    await GET(request)

    expect(mockListarHospitais).toHaveBeenCalledWith(expect.anything(), {
      excluirBloqueados: false,
      apenasRevisados: false,
      limit: 50,
    })
  })

  it('deve passar search quando parametro fornecido', async () => {
    mockListarHospitais.mockResolvedValue([])

    const request = createRequest({ search: 'São Luiz' })
    await GET(request)

    expect(mockListarHospitais).toHaveBeenCalledWith(expect.anything(), {
      excluirBloqueados: false,
      apenasRevisados: true,
      limit: 50,
      search: 'São Luiz',
    })
  })

  it('deve respeitar limit customizado', async () => {
    mockListarHospitais.mockResolvedValue([])

    const request = createRequest({ limit: '20' })
    await GET(request)

    expect(mockListarHospitais).toHaveBeenCalledWith(expect.anything(), {
      excluirBloqueados: false,
      apenasRevisados: true,
      limit: 20,
    })
  })
})

// =============================================================================
// POST /api/hospitais
// =============================================================================

function createPostRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/hospitais', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

describe('POST /api/hospitais', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve criar hospital com nome, cidade e estado', async () => {
    mockSingle.mockResolvedValue({
      data: { id: 'new-hospital-id', nome: 'Hospital Novo' },
      error: null,
    })

    const request = createPostRequest({ nome: 'Hospital Novo', cidade: 'São Paulo', estado: 'SP' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(201)
    expect(data.id).toBe('new-hospital-id')
    expect(data.nome).toBe('Hospital Novo')
    expect(mockAdminFrom).toHaveBeenCalledWith('hospitais')
    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        nome: 'Hospital Novo',
        cidade: 'São Paulo',
        estado: 'SP',
        precisa_revisao: true,
        endereco_verificado: false,
      })
    )
  })

  it('deve retornar 400 quando nome esta vazio', async () => {
    const request = createPostRequest({ nome: '', cidade: 'SP', estado: 'SP' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome e obrigatorio')
  })

  it('deve retornar 400 quando nome nao e string', async () => {
    const request = createPostRequest({ nome: 123, cidade: 'SP', estado: 'SP' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome e obrigatorio')
  })

  it('deve retornar 400 quando nome e apenas espacos', async () => {
    const request = createPostRequest({ nome: '   ', cidade: 'SP', estado: 'SP' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome e obrigatorio')
  })

  it('deve retornar 400 quando body nao tem nome', async () => {
    const request = createPostRequest({})
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome e obrigatorio')
  })

  it('deve retornar 400 quando cidade esta vazia', async () => {
    const request = createPostRequest({ nome: 'Hospital A', cidade: '', estado: 'SP' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Cidade e obrigatoria')
  })

  it('deve retornar 400 quando cidade nao fornecida', async () => {
    const request = createPostRequest({ nome: 'Hospital A', estado: 'SP' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Cidade e obrigatoria')
  })

  it('deve retornar 400 quando estado esta vazio', async () => {
    const request = createPostRequest({ nome: 'Hospital A', cidade: 'São Paulo', estado: '' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Estado e obrigatorio')
  })

  it('deve retornar 400 quando estado nao fornecido', async () => {
    const request = createPostRequest({ nome: 'Hospital A', cidade: 'São Paulo' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Estado e obrigatorio')
  })

  it('deve setar endereco_verificado true quando lat/long presentes', async () => {
    mockSingle.mockResolvedValue({
      data: { id: 'id', nome: 'Hospital Geo' },
      error: null,
    })

    const request = createPostRequest({
      nome: 'Hospital Geo',
      cidade: 'São Paulo',
      estado: 'SP',
      latitude: -23.55,
      longitude: -46.63,
    })
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        endereco_verificado: true,
        precisa_revisao: false,
        latitude: -23.55,
        longitude: -46.63,
      })
    )
  })

  it('deve setar precisa_revisao true quando sem lat/long', async () => {
    mockSingle.mockResolvedValue({
      data: { id: 'id', nome: 'Hospital Sem Geo' },
      error: null,
    })

    const request = createPostRequest({
      nome: 'Hospital Sem Geo',
      cidade: 'São Paulo',
      estado: 'SP',
    })
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        endereco_verificado: false,
        precisa_revisao: true,
      })
    )
  })

  it('deve retornar 500 quando banco retorna erro', async () => {
    mockSingle.mockResolvedValue({
      data: null,
      error: { message: 'Duplicate key' },
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createPostRequest({
      nome: 'Hospital Duplicado',
      cidade: 'São Paulo',
      estado: 'SP',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao criar hospital')

    consoleSpy.mockRestore()
  })

  it('deve fazer trim no nome', async () => {
    mockSingle.mockResolvedValue({
      data: { id: 'id', nome: 'Hospital Trim' },
      error: null,
    })

    const request = createPostRequest({
      nome: '  Hospital Trim  ',
      cidade: 'São Paulo',
      estado: 'SP',
    })
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith(expect.objectContaining({ nome: 'Hospital Trim' }))
  })
})
