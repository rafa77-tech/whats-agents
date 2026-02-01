/**
 * Testes para POST /api/hospitais/desbloquear
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { POST } from '@/app/api/hospitais/desbloquear/route'
import { NextRequest } from 'next/server'

// Mocks do repository
const mockVerificarHospitalBloqueado = vi.fn()
const mockDesbloquearHospital = vi.fn()
const mockRegistrarAuditLog = vi.fn()

vi.mock('@/lib/hospitais', () => ({
  verificarHospitalBloqueado: (...args: unknown[]) => mockVerificarHospitalBloqueado(...args),
  desbloquearHospital: (...args: unknown[]) => mockDesbloquearHospital(...args),
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
  return new NextRequest('http://localhost:3000/api/hospitais/desbloquear', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('POST /api/hospitais/desbloquear', () => {
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

  it('deve desbloquear hospital com sucesso', async () => {
    mockVerificarHospitalBloqueado.mockResolvedValue({
      bloqueado: true,
      bloqueio: {
        id: 'b1',
        hospital_id: 'h1',
        hospitais: { nome: 'Hospital A' },
      },
    })
    mockDesbloquearHospital.mockResolvedValue({ success: true, vagas_restauradas: 2 })
    mockRegistrarAuditLog.mockResolvedValue(undefined)

    const request = createRequest({ hospital_id: 'h1' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(200)
    expect(data.success).toBe(true)
    expect(data.vagas_restauradas).toBe(2)
    expect(mockDesbloquearHospital).toHaveBeenCalledWith(
      expect.anything(),
      'h1',
      'b1',
      'admin@test.com'
    )
    expect(mockRegistrarAuditLog).toHaveBeenCalledWith(
      expect.anything(),
      'hospital_desbloqueado',
      'admin@test.com',
      expect.objectContaining({
        hospital_id: 'h1',
        hospital_nome: 'Hospital A',
        vagas_restauradas: 2,
      })
    )
  })

  it('deve retornar 401 quando usuario nao autenticado', async () => {
    mockGetUser.mockResolvedValue({ data: { user: null } })

    const request = createRequest({ hospital_id: 'h1' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(401)
    expect(data.detail).toBe('Não autorizado')
  })

  it('deve retornar 400 quando hospital_id falta', async () => {
    const request = createRequest({})
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(400)
    expect(data.detail).toBe('hospital_id é obrigatório')
  })

  it('deve retornar 404 quando hospital nao esta bloqueado', async () => {
    mockVerificarHospitalBloqueado.mockResolvedValue({ bloqueado: false })

    const request = createRequest({ hospital_id: 'h1' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(404)
    expect(data.detail).toBe('Hospital não está bloqueado')
  })

  it('deve retornar 500 quando desbloquear falha', async () => {
    mockVerificarHospitalBloqueado.mockResolvedValue({
      bloqueado: true,
      bloqueio: { id: 'b1', hospital_id: 'h1' },
    })
    mockDesbloquearHospital.mockRejectedValue(new Error('DB Error'))

    const request = createRequest({ hospital_id: 'h1' })
    const response = await POST(request)
    const data = await response.json()

    expect(response.status).toBe(500)
    expect(data.detail).toBe('DB Error')
  })

  it('deve usar desconhecido como nome do hospital quando nao disponivel', async () => {
    mockVerificarHospitalBloqueado.mockResolvedValue({
      bloqueado: true,
      bloqueio: {
        id: 'b1',
        hospital_id: 'h1',
        // hospitais nao presente
      },
    })
    mockDesbloquearHospital.mockResolvedValue({ success: true, vagas_restauradas: 0 })
    mockRegistrarAuditLog.mockResolvedValue(undefined)

    const request = createRequest({ hospital_id: 'h1' })
    await POST(request)

    expect(mockRegistrarAuditLog).toHaveBeenCalledWith(
      expect.anything(),
      'hospital_desbloqueado',
      'admin@test.com',
      expect.objectContaining({
        hospital_nome: 'desconhecido',
      })
    )
  })

  it('deve usar desconhecido quando usuario nao tem email', async () => {
    mockGetUser.mockResolvedValue({
      data: { user: { email: null } },
    })
    mockVerificarHospitalBloqueado.mockResolvedValue({
      bloqueado: true,
      bloqueio: { id: 'b1', hospital_id: 'h1' },
    })
    mockDesbloquearHospital.mockResolvedValue({ success: true, vagas_restauradas: 0 })
    mockRegistrarAuditLog.mockResolvedValue(undefined)

    const request = createRequest({ hospital_id: 'h1' })
    await POST(request)

    expect(mockDesbloquearHospital).toHaveBeenCalledWith(
      expect.anything(),
      'h1',
      'b1',
      'desconhecido'
    )
  })
})
