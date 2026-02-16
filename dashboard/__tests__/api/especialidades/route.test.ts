/**
 * Testes para GET /api/especialidades e POST /api/especialidades
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, POST } from '@/app/api/especialidades/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient (used by both GET and POST)
const mockOrder = vi.fn()
const mockGetSelect = vi.fn(() => ({ order: mockOrder }))
const mockSingle = vi.fn()
const mockPostSelectChain = vi.fn(() => ({ single: mockSingle }))
const mockInsert = vi.fn(() => ({ select: mockPostSelectChain }))
const mockAdminFrom = vi.fn((_table: string) => {
  // GET uses select().order(), POST uses insert().select().single()
  return { select: mockGetSelect, insert: mockInsert }
})

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => ({ from: mockAdminFrom }),
}))

describe('GET /api/especialidades', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve retornar lista de especialidades', async () => {
    const mockData = [
      { id: 'e1', nome: 'Cardiologia' },
      { id: 'e2', nome: 'Ortopedia' },
    ]
    mockOrder.mockResolvedValue({ data: mockData, error: null })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual(mockData)
    expect(mockAdminFrom).toHaveBeenCalledWith('especialidades')
    expect(mockGetSelect).toHaveBeenCalledWith('id, nome')
  })

  it('deve retornar array vazio quando nao ha especialidades', async () => {
    mockOrder.mockResolvedValue({ data: [], error: null })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })

  it('deve retornar array vazio quando data e null', async () => {
    mockOrder.mockResolvedValue({ data: null, error: null })

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data).toEqual([])
  })

  it('deve retornar 500 quando banco retorna erro', async () => {
    mockOrder.mockResolvedValue({ data: null, error: { message: 'DB error' } })
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const response = await GET()
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao buscar especialidades')

    consoleSpy.mockRestore()
  })

  it('nao deve filtrar por coluna ativo', async () => {
    mockOrder.mockResolvedValue({ data: [], error: null })

    await GET()

    // Verify that select was called without .eq('ativo', true)
    expect(mockGetSelect).toHaveBeenCalledWith('id, nome')
    // The chain goes: from -> select -> order (no eq in between)
    expect(mockGetSelect).toHaveReturnedWith({ order: mockOrder })
  })
})

// =============================================================================
// POST /api/especialidades
// =============================================================================

function createPostRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/especialidades', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

describe('POST /api/especialidades', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve criar especialidade com nome valido', async () => {
    mockSingle.mockResolvedValue({
      data: { id: 'new-esp-id', nome: 'Neurologia' },
      error: null,
    })

    const request = createPostRequest({ nome: 'Neurologia' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(201)
    expect(data.id).toBe('new-esp-id')
    expect(data.nome).toBe('Neurologia')
    expect(mockAdminFrom).toHaveBeenCalledWith('especialidades')
    expect(mockInsert).toHaveBeenCalledWith({ nome: 'Neurologia' })
  })

  it('deve retornar 400 quando nome esta vazio', async () => {
    const request = createPostRequest({ nome: '' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome e obrigatorio')
  })

  it('deve retornar 400 quando nome nao e string', async () => {
    const request = createPostRequest({ nome: 123 })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Nome e obrigatorio')
  })

  it('deve retornar 400 quando nome e apenas espacos', async () => {
    const request = createPostRequest({ nome: '   ' })
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

  it('deve retornar 500 quando banco retorna erro', async () => {
    mockSingle.mockResolvedValue({
      data: null,
      error: { message: 'Duplicate key' },
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createPostRequest({ nome: 'Duplicada' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('Erro ao criar especialidade')

    consoleSpy.mockRestore()
  })

  it('deve fazer trim no nome', async () => {
    mockSingle.mockResolvedValue({
      data: { id: 'id', nome: 'Pediatria' },
      error: null,
    })

    const request = createPostRequest({ nome: '  Pediatria  ' })
    await POST(request)

    expect(mockInsert).toHaveBeenCalledWith({ nome: 'Pediatria' })
  })
})
