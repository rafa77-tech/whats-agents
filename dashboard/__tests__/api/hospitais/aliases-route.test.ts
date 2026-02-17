/**
 * Testes para POST/DELETE /api/hospitais/[id]/aliases
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { POST, DELETE } from '@/app/api/hospitais/[id]/aliases/route'
import { NextRequest } from 'next/server'

const mockAdicionarAlias = vi.fn()
const mockRemoverAlias = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  adicionarAlias: (...args: unknown[]) => mockAdicionarAlias(...args),
  removerAlias: (...args: unknown[]) => mockRemoverAlias(...args),
}))

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => ({}),
}))

const HOSPITAL_ID = '123e4567-e89b-12d3-a456-426614174000'
const ALIAS_ID = '323e4567-e89b-12d3-a456-426614174002'
const routeParams = { params: Promise.resolve({ id: HOSPITAL_ID }) }

describe('POST /api/hospitais/[id]/aliases', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('deve adicionar alias com sucesso', async () => {
    mockAdicionarAlias.mockResolvedValue({ success: true })

    const request = new NextRequest(`http://localhost:3000/api/hospitais/${HOSPITAL_ID}/aliases`, {
      method: 'POST',
      body: JSON.stringify({ alias: 'Hospital Novo Nome' }),
      headers: { 'Content-Type': 'application/json' },
    })
    const response = await POST(request, routeParams)

    expect(response.status).toBe(201)
    expect(mockAdicionarAlias).toHaveBeenCalledWith(
      expect.anything(),
      HOSPITAL_ID,
      'Hospital Novo Nome',
      expect.any(String)
    )
  })

  it('deve retornar 400 se alias vazio', async () => {
    const request = new NextRequest(`http://localhost:3000/api/hospitais/${HOSPITAL_ID}/aliases`, {
      method: 'POST',
      body: JSON.stringify({ alias: '' }),
      headers: { 'Content-Type': 'application/json' },
    })
    const response = await POST(request, routeParams)

    expect(response.status).toBe(400)
  })

  it('deve retornar 400 se alias nao fornecido', async () => {
    const request = new NextRequest(`http://localhost:3000/api/hospitais/${HOSPITAL_ID}/aliases`, {
      method: 'POST',
      body: JSON.stringify({}),
      headers: { 'Content-Type': 'application/json' },
    })
    const response = await POST(request, routeParams)

    expect(response.status).toBe(400)
  })
})

describe('DELETE /api/hospitais/[id]/aliases', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('deve remover alias com sucesso', async () => {
    mockRemoverAlias.mockResolvedValue(undefined)

    const request = new NextRequest(
      `http://localhost:3000/api/hospitais/${HOSPITAL_ID}/aliases?alias_id=${ALIAS_ID}`,
      { method: 'DELETE' }
    )
    const response = await DELETE(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockRemoverAlias).toHaveBeenCalledWith(expect.anything(), ALIAS_ID)
  })

  it('deve retornar 400 se alias_id nao fornecido', async () => {
    const request = new NextRequest(`http://localhost:3000/api/hospitais/${HOSPITAL_ID}/aliases`, {
      method: 'DELETE',
    })
    const response = await DELETE(request)

    expect(response.status).toBe(400)
  })
})
