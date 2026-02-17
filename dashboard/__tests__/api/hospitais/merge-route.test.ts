/**
 * Testes para POST /api/hospitais/[id]/merge
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { POST } from '@/app/api/hospitais/[id]/merge/route'
import { NextRequest } from 'next/server'

const mockMesclarHospitais = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  mesclarHospitais: (...args: unknown[]) => mockMesclarHospitais(...args),
}))

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => ({}),
}))

const HOSPITAL_ID = '123e4567-e89b-12d3-a456-426614174000'
const DUPLICADO_ID = '223e4567-e89b-12d3-a456-426614174001'
const routeParams = { params: Promise.resolve({ id: HOSPITAL_ID }) }

function createRequest(body: Record<string, unknown>) {
  return new NextRequest(`http://localhost:3000/api/hospitais/${HOSPITAL_ID}/merge`, {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('POST /api/hospitais/[id]/merge', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('deve mesclar hospitais com sucesso', async () => {
    const mockResult = { vagas_migradas: 5, aliases_migrados: 2 }
    mockMesclarHospitais.mockResolvedValue(mockResult)

    const request = createRequest({ duplicado_id: DUPLICADO_ID })
    const response = await POST(request, routeParams)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.vagas_migradas).toBe(5)
    expect(mockMesclarHospitais).toHaveBeenCalledWith(
      expect.anything(),
      HOSPITAL_ID,
      DUPLICADO_ID,
      'dashboard'
    )
  })

  it('deve retornar 400 se duplicado_id nao fornecido', async () => {
    const request = createRequest({})
    const response = await POST(request, routeParams)

    expect(response.status).toBe(400)
  })

  it('deve retornar 500 se merge falhar', async () => {
    mockMesclarHospitais.mockRejectedValue(new Error('Merge failed'))

    const request = createRequest({ duplicado_id: DUPLICADO_ID })
    const response = await POST(request, routeParams)

    expect(response.status).toBe(500)
  })
})
