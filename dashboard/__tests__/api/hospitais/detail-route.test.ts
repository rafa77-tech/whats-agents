/**
 * Testes para GET/PATCH/DELETE /api/hospitais/[id]
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { GET, PATCH, DELETE } from '@/app/api/hospitais/[id]/route'
import { NextRequest } from 'next/server'

const mockBuscarHospitalDetalhado = vi.fn()
const mockAtualizarHospital = vi.fn()
const mockDeletarHospitalSeguro = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  buscarHospitalDetalhado: (...args: unknown[]) => mockBuscarHospitalDetalhado(...args),
  atualizarHospital: (...args: unknown[]) => mockAtualizarHospital(...args),
  deletarHospitalSeguro: (...args: unknown[]) => mockDeletarHospitalSeguro(...args),
}))

vi.mock('@/lib/supabase/admin', () => ({
  createAdminClient: () => ({}),
}))

const HOSPITAL_ID = '123e4567-e89b-12d3-a456-426614174000'
const routeParams = { params: Promise.resolve({ id: HOSPITAL_ID }) }

function createRequest(method: string, body?: Record<string, unknown>) {
  const url = `http://localhost:3000/api/hospitais/${HOSPITAL_ID}`
  if (body) {
    return new NextRequest(url, {
      method,
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
    })
  }
  return new NextRequest(url, { method })
}

describe('GET /api/hospitais/[id]', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('deve retornar hospital detalhado', async () => {
    const mockHospital = { id: HOSPITAL_ID, nome: 'Hospital Test', aliases: [], vagas_count: 3 }
    mockBuscarHospitalDetalhado.mockResolvedValue(mockHospital)

    const request = createRequest('GET')
    const response = await GET(request, routeParams)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.nome).toBe('Hospital Test')
  })

  it('deve retornar 404 se hospital nao encontrado', async () => {
    mockBuscarHospitalDetalhado.mockResolvedValue(null)

    const request = createRequest('GET')
    const response = await GET(request, routeParams)

    expect(response.status).toBe(404)
  })

  it('deve retornar 500 em caso de erro', async () => {
    mockBuscarHospitalDetalhado.mockRejectedValue(new Error('DB error'))

    const request = createRequest('GET')
    const response = await GET(request, routeParams)

    expect(response.status).toBe(500)
  })
})

describe('PATCH /api/hospitais/[id]', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('deve atualizar hospital com campos validos', async () => {
    mockAtualizarHospital.mockResolvedValue(undefined)

    const request = createRequest('PATCH', { nome: 'Novo Nome', cidade: 'SP' })
    const response = await PATCH(request, routeParams)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(mockAtualizarHospital).toHaveBeenCalledWith(
      expect.anything(),
      HOSPITAL_ID,
      expect.objectContaining({ nome: 'Novo Nome', cidade: 'SP' })
    )
  })

  it('deve retornar 400 se nenhum campo enviado', async () => {
    const request = createRequest('PATCH', {})
    const response = await PATCH(request, routeParams)

    expect(response.status).toBe(400)
  })

  it('deve aceitar campo precisa_revisao booleano', async () => {
    mockAtualizarHospital.mockResolvedValue(undefined)

    const request = createRequest('PATCH', { precisa_revisao: false })
    const response = await PATCH(request, routeParams)

    expect(response.status).toBe(200)
    expect(mockAtualizarHospital).toHaveBeenCalledWith(expect.anything(), HOSPITAL_ID, {
      precisa_revisao: false,
    })
  })
})

describe('DELETE /api/hospitais/[id]', () => {
  beforeEach(() => vi.clearAllMocks())
  afterEach(() => vi.restoreAllMocks())

  it('deve deletar hospital sem referencias', async () => {
    mockDeletarHospitalSeguro.mockResolvedValue(true)

    const request = createRequest('DELETE')
    const response = await DELETE(request, routeParams)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
  })

  it('deve retornar 409 se hospital tem referencias', async () => {
    mockDeletarHospitalSeguro.mockResolvedValue(false)

    const request = createRequest('DELETE')
    const response = await DELETE(request, routeParams)

    expect(response.status).toBe(409)
  })
})
