/**
 * Testes para POST /api/hospitais/bloquear
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { POST } from '@/app/api/hospitais/bloquear/route'
import { NextRequest } from 'next/server'

// Mocks do repository
const mockVerificarHospitalExiste = vi.fn()
const mockVerificarHospitalBloqueado = vi.fn()
const mockBloquearHospital = vi.fn()
const mockRegistrarAuditLog = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  verificarHospitalExiste: (...args: unknown[]) => mockVerificarHospitalExiste(...args),
  verificarHospitalBloqueado: (...args: unknown[]) => mockVerificarHospitalBloqueado(...args),
  bloquearHospital: (...args: unknown[]) => mockBloquearHospital(...args),
  registrarAuditLog: (...args: unknown[]) => mockRegistrarAuditLog(...args),
}))

// Mock createClient com auth
const mockGetUser = vi.fn()

vi.mock('@/lib/supabase/server', () => ({
  createClient: () =>
    Promise.resolve({
      auth: {
        getUser: () => mockGetUser(),
      },
    }),
}))

function createRequest(body: Record<string, unknown>) {
  return new NextRequest('http://localhost:3000/api/hospitais/bloquear', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('POST /api/hospitais/bloquear', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    // Default: usuario autenticado
    mockGetUser.mockResolvedValue({
      data: { user: { email: 'admin@test.com' } },
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('deve bloquear hospital com sucesso', async () => {
    mockVerificarHospitalExiste.mockResolvedValue({
      existe: true,
      hospital: { id: 'h1', nome: 'Hospital A' },
    })
    mockVerificarHospitalBloqueado.mockResolvedValue({ bloqueado: false })
    mockBloquearHospital.mockResolvedValue({ success: true, vagas_movidas: 3 })
    mockRegistrarAuditLog.mockResolvedValue(undefined)

    const request = createRequest({
      hospital_id: 'h1',
      motivo: 'Pagamento atrasado',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(data.vagas_movidas).toBe(3)
    expect(mockBloquearHospital).toHaveBeenCalledWith(
      expect.anything(),
      'h1',
      'Pagamento atrasado',
      'admin@test.com'
    )
    expect(mockRegistrarAuditLog).toHaveBeenCalledWith(
      expect.anything(),
      'hospital_bloqueado',
      'admin@test.com',
      expect.objectContaining({
        hospital_id: 'h1',
        hospital_nome: 'Hospital A',
        motivo: 'Pagamento atrasado',
        vagas_movidas: 3,
      })
    )
  })

  it('deve retornar 401 quando usuario nao autenticado', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } })

    const request = createRequest({
      hospital_id: 'h1',
      motivo: 'Teste',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.detail).toBe('Não autorizado')
  })

  it('deve retornar 400 quando hospital_id falta', async () => {
    const request = createRequest({ motivo: 'Teste' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('hospital_id e motivo são obrigatórios')
  })

  it('deve retornar 400 quando motivo falta', async () => {
    const request = createRequest({ hospital_id: 'h1' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('hospital_id e motivo são obrigatórios')
  })

  it('deve retornar 404 quando hospital nao existe', async () => {
    mockVerificarHospitalExiste.mockResolvedValue({ existe: false })

    const request = createRequest({
      hospital_id: 'h999',
      motivo: 'Teste',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(404)
    expect(data.detail).toBe('Hospital não encontrado')
  })

  it('deve retornar 400 quando hospital ja esta bloqueado', async () => {
    mockVerificarHospitalExiste.mockResolvedValue({
      existe: true,
      hospital: { id: 'h1', nome: 'Hospital A' },
    })
    mockVerificarHospitalBloqueado.mockResolvedValue({ bloqueado: true })

    const request = createRequest({
      hospital_id: 'h1',
      motivo: 'Teste',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('Hospital já está bloqueado')
  })

  it('deve retornar 500 quando bloquear falha', async () => {
    mockVerificarHospitalExiste.mockResolvedValue({
      existe: true,
      hospital: { id: 'h1', nome: 'Hospital A' },
    })
    mockVerificarHospitalBloqueado.mockResolvedValue({ bloqueado: false })
    mockBloquearHospital.mockRejectedValue(new Error('DB Error'))

    const request = createRequest({
      hospital_id: 'h1',
      motivo: 'Teste',
    })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('DB Error')
  })

  it('deve usar desconhecido quando usuario nao tem email', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: null } },
    })
    mockVerificarHospitalExiste.mockResolvedValue({
      existe: true,
      hospital: { id: 'h1', nome: 'Hospital A' },
    })
    mockVerificarHospitalBloqueado.mockResolvedValue({ bloqueado: false })
    mockBloquearHospital.mockResolvedValue({ success: true, vagas_movidas: 0 })
    mockRegistrarAuditLog.mockResolvedValue(undefined)

    const request = createRequest({
      hospital_id: 'h1',
      motivo: 'Teste',
    })
    await POST(request)

    expect(mockBloquearHospital).toHaveBeenCalledWith(
      expect.anything(),
      'h1',
      'Teste',
      'desconhecido'
    )
  })
})
