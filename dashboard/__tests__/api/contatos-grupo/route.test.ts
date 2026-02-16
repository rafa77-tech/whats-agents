/**
 * Testes para GET /api/contatos-grupo
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET } from '@/app/api/contatos-grupo/route'
import { NextRequest } from 'next/server'

// Mock createAdminClient
const mockSelect = vi.fn()
const mockNot = vi.fn()
const mockOrder = vi.fn()
const mockLimit = vi.fn()
const mockOr = vi.fn()

const mockFrom = vi.fn(() => ({
  select: mockSelect,
}))

const mockSupabase = {
  from: mockFrom,
}

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => mockSupabase,
}))

function createRequest(params: Record<string, string> = {}) {
  const searchParams = new URLSearchParams(params)
  const url = `http://localhost:3000/api/contatos-grupo?${searchParams}`
  return new NextRequest(url)
}

function setupChain(resolvedValue: { data: unknown[] | null; error: unknown | null }) {
  mockLimit.mockResolvedValue(resolvedValue)
  mockOrder.mockReturnValue({ limit: mockLimit })
  mockNot.mockReturnValue({ order: mockOrder })
  mockSelect.mockReturnValue({ not: mockNot })
  // For queries with .or() after .not()
  mockOr.mockReturnValue({
    order: vi.fn().mockReturnValue({ limit: vi.fn().mockResolvedValue(resolvedValue) }),
  })
}

describe('GET /api/contatos-grupo', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns contatos list', async () => {
    const mockContatos = [
      { id: 'c1', nome: 'Maria Silva', telefone: '5511999999999', empresa: 'MedStaff' },
      { id: 'c2', nome: 'Joao Santos', telefone: '5511888888888', empresa: null },
    ]

    setupChain({ data: mockContatos, error: null })

    const request = createRequest()
    const response = await GET(request)
    const json = await response.json()

    expect(response.status).toBe(200)
    expect(json.data).toHaveLength(2)
    expect(json.data[0].nome).toBe('Maria Silva')
    expect(mockFrom).toHaveBeenCalledWith('contatos_grupo')
    expect(mockSelect).toHaveBeenCalledWith('id, nome, telefone, empresa')
  })

  it('returns empty data on error', async () => {
    setupChain({ data: null, error: { message: 'Database error' } })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const json = await response.json()

    expect(response.status).toBe(200)
    expect(json.data).toEqual([])

    consoleSpy.mockRestore()
  })

  it('returns empty data on null result', async () => {
    setupChain({ data: null, error: null })

    const request = createRequest()
    const response = await GET(request)
    const json = await response.json()

    expect(response.status).toBe(200)
    expect(json.data).toEqual([])
  })

  it('handles exception gracefully', async () => {
    mockSelect.mockImplementation(() => {
      throw new Error('Unexpected')
    })

    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})

    const request = createRequest()
    const response = await GET(request)
    const json = await response.json()

    expect(response.status).toBe(200)
    expect(json.data).toEqual([])

    consoleSpy.mockRestore()
  })
})
