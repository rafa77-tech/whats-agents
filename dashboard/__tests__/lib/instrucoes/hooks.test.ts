/**
 * Testes para lib/instrucoes/hooks.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useInstrucoes, useNovaInstrucao, useInstrucaoForm } from '@/lib/instrucoes/hooks'
import type { Diretriz } from '@/lib/instrucoes/types'

// =============================================================================
// Mocks
// =============================================================================

const mockFetch = vi.fn()

beforeEach(() => {
  vi.stubGlobal('fetch', mockFetch)
  mockFetch.mockReset()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

// =============================================================================
// useInstrucoes
// =============================================================================

describe('useInstrucoes', () => {
  const mockDiretrizes: Diretriz[] = [
    {
      id: '1',
      tipo: 'margem_negociacao',
      escopo: 'global',
      conteudo: { valor_maximo: 3000 },
      criado_por: 'admin@test.com',
      criado_em: '2024-01-15T10:00:00Z',
      status: 'ativa',
    },
  ]

  it('deve iniciar com loading true', () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDiretrizes),
    })

    const { result } = renderHook(() => useInstrucoes())

    expect(result.current.loading).toBe(true)
    expect(result.current.diretrizes).toEqual([])
  })

  it('deve carregar diretrizes no mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDiretrizes),
    })

    const { result } = renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.diretrizes).toHaveLength(1)
    expect(result.current.diretrizes[0]?.tipo).toBe('margem_negociacao')
  })

  it('deve chamar API com status correto para tab ativas', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })

    renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('status=ativa')
  })

  it('deve chamar API com status correto para tab historico', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    })

    const { result } = renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    act(() => {
      result.current.actions.setTab('historico')
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('expirada')
    expect(calledUrl).toContain('cancelada')
  })

  it('deve tratar erro de API', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ detail: 'Erro de teste' }),
    })

    const { result } = renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Erro de teste')
    expect(result.current.diretrizes).toEqual([])
  })

  it('deve tratar erro de conexao', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Erro de conexao com o servidor')
  })

  it('deve permitir refresh manual', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockDiretrizes),
    })

    const { result } = renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    await act(async () => {
      await result.current.actions.refresh()
    })

    expect(mockFetch).toHaveBeenCalled()
  })

  it('deve cancelar diretriz', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDiretrizes),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ status: 'cancelada' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })

    const { result } = renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.actions.cancelar(mockDiretrizes[0]!)
    })

    // Verifica que PATCH foi chamado
    const patchCall = mockFetch.mock.calls.find(
      (call) => call[1]?.method === 'PATCH'
    )
    expect(patchCall).toBeDefined()
  })

  it('deve lancar erro ao cancelar com falha', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockDiretrizes),
      })
      .mockResolvedValueOnce({
        ok: false,
      })

    const { result } = renderHook(() => useInstrucoes())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await expect(
      act(async () => {
        await result.current.actions.cancelar(mockDiretrizes[0]!)
      })
    ).rejects.toThrow('Erro ao cancelar diretriz')
  })
})

// =============================================================================
// useNovaInstrucao
// =============================================================================

describe('useNovaInstrucao', () => {
  const mockHospitais = [{ id: '1', nome: 'Hospital A' }]
  const mockEspecialidades = [{ id: '1', nome: 'Cardiologia' }]

  it('deve carregar listas no mount', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockHospitais),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockEspecialidades),
      })

    const { result } = renderHook(() => useNovaInstrucao())

    await waitFor(() => {
      expect(result.current.loadingListas).toBe(false)
    })

    expect(result.current.hospitais).toHaveLength(1)
    expect(result.current.especialidades).toHaveLength(1)
  })

  it('deve criar diretriz com sucesso', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: '1' }),
      })

    const { result } = renderHook(() => useNovaInstrucao())

    await waitFor(() => {
      expect(result.current.loadingListas).toBe(false)
    })

    let success = false
    await act(async () => {
      success = await result.current.criar({
        tipo: 'margem_negociacao',
        escopo: 'global',
        conteudo: { valor_maximo: 3000 },
      })
    })

    expect(success).toBe(true)
  })

  it('deve retornar false ao criar com erro', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve([]),
      })
      .mockResolvedValueOnce({
        ok: false,
      })

    const { result } = renderHook(() => useNovaInstrucao())

    await waitFor(() => {
      expect(result.current.loadingListas).toBe(false)
    })

    let success = true
    await act(async () => {
      success = await result.current.criar({
        tipo: 'margem_negociacao',
        escopo: 'global',
        conteudo: { valor_maximo: 3000 },
      })
    })

    expect(success).toBe(false)
  })
})

// =============================================================================
// useInstrucaoForm
// =============================================================================

describe('useInstrucaoForm', () => {
  it('deve iniciar com valores default', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    expect(result.current.form.tipo).toBe('margem_negociacao')
    expect(result.current.form.escopo).toBe('global')
    expect(result.current.form.hospitalId).toBe('')
  })

  it('deve atualizar campo', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('tipo', 'regra_especial')
    })

    expect(result.current.form.tipo).toBe('regra_especial')
  })

  it('deve resetar form', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('tipo', 'regra_especial')
      result.current.updateField('regra', 'Teste')
    })

    act(() => {
      result.current.reset()
    })

    expect(result.current.form.tipo).toBe('margem_negociacao')
    expect(result.current.form.regra).toBe('')
  })

  it('deve validar canSubmit para margem_negociacao', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    // Sem valor nem percentual
    expect(result.current.canSubmit()).toBe(false)

    // Com valor
    act(() => {
      result.current.updateField('valorMaximo', '3000')
    })
    expect(result.current.canSubmit()).toBe(true)
  })

  it('deve validar canSubmit para regra_especial', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('tipo', 'regra_especial')
    })

    // Sem regra
    expect(result.current.canSubmit()).toBe(false)

    // Com regra
    act(() => {
      result.current.updateField('regra', 'Regra de teste')
    })
    expect(result.current.canSubmit()).toBe(true)
  })

  it('deve validar canSubmit para escopo hospital', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('valorMaximo', '3000')
      result.current.updateField('escopo', 'hospital')
    })

    // Sem hospitalId
    expect(result.current.canSubmit()).toBe(false)

    // Com hospitalId
    act(() => {
      result.current.updateField('hospitalId', '123')
    })
    expect(result.current.canSubmit()).toBe(true)
  })

  it('deve construir payload corretamente para margem', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('valorMaximo', '3000')
    })

    const payload = result.current.buildPayload()

    expect(payload.tipo).toBe('margem_negociacao')
    expect(payload.escopo).toBe('global')
    expect(payload.conteudo.valor_maximo).toBe(3000)
  })

  it('deve construir payload corretamente para regra', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('tipo', 'regra_especial')
      result.current.updateField('regra', 'Regra de teste')
    })

    const payload = result.current.buildPayload()

    expect(payload.tipo).toBe('regra_especial')
    expect(payload.conteudo.regra).toBe('Regra de teste')
  })

  it('deve incluir hospital_id no payload quando escopo hospital', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('escopo', 'hospital')
      result.current.updateField('hospitalId', '123')
      result.current.updateField('valorMaximo', '3000')
    })

    const payload = result.current.buildPayload()

    expect(payload.hospital_id).toBe('123')
  })

  it('deve incluir expira_em no payload quando definido', () => {
    const { result } = renderHook(() => useInstrucaoForm())

    act(() => {
      result.current.updateField('valorMaximo', '3000')
      result.current.updateField('expiraEm', '2024-12-31T12:00')
    })

    const payload = result.current.buildPayload()

    expect(payload.expira_em).toBeDefined()
    // Verifica que e uma data ISO valida
    expect(new Date(payload.expira_em!).toISOString()).toBe(payload.expira_em)
  })
})
