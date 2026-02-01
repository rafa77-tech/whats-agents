/**
 * Testes para lib/qualidade/hooks.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import {
  useQualidadeMetrics,
  useConversations,
  useConversationDetail,
  useSuggestions,
} from '@/lib/qualidade/hooks'

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
// useQualidadeMetrics
// =============================================================================

describe('useQualidadeMetrics', () => {
  it('deve iniciar com loading true', () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useQualidadeMetrics())

    expect(result.current.loading).toBe(true)
    expect(result.current.metrics).toBeNull()
  })

  it('deve buscar metricas com sucesso', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ avaliadas: 10, pendentes: 5, score_medio: 4.2 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ taxa_sucesso: 95, falhas: 5, padroes_violados: [] }),
      })

    const { result } = renderHook(() => useQualidadeMetrics())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.metrics).not.toBeNull()
    expect(result.current.metrics!.avaliadas).toBe(10)
    expect(result.current.metrics!.validacaoTaxa).toBe(95)
    expect(result.current.error).toBeNull()
  })

  it('deve usar valores default quando API falha', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useQualidadeMetrics())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.metrics!.avaliadas).toBe(0)
    expect(result.current.metrics!.validacaoTaxa).toBe(98)
  })

  it('deve permitir refresh', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ avaliadas: 10 }),
    })

    const { result } = renderHook(() => useQualidadeMetrics())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Resetar mock para verificar nova chamada
    mockFetch.mockClear()
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ avaliadas: 20 }),
    })

    await act(async () => {
      await result.current.refresh()
    })

    expect(mockFetch).toHaveBeenCalled()
  })
})

// =============================================================================
// useConversations
// =============================================================================

describe('useConversations', () => {
  it('deve buscar conversas com filtro default', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          conversas: [
            {
              id: 'conv1',
              medico_nome: 'Dr. Silva',
              total_mensagens: 10,
              status: 'ativa',
              avaliada: false,
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    const { result } = renderHook(() => useConversations())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.conversations).toHaveLength(1)
    expect(result.current.conversations[0]!.medicoNome).toBe('Dr. Silva')
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('avaliada=false'))
  })

  it('deve buscar todas as conversas quando filtro e "all"', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conversas: [] }),
    })

    renderHook(() => useConversations('all'))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]![0] as string
    expect(calledUrl).not.toContain('avaliada=')
  })

  it('deve retornar array vazio em caso de erro', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useConversations())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.conversations).toEqual([])
    expect(result.current.error).not.toBeNull()
  })

  it('deve atualizar quando filtro muda', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ conversas: [] }),
    })

    const { rerender } = renderHook(({ filter }) => useConversations(filter), {
      initialProps: { filter: 'false' },
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    mockFetch.mockClear()

    rerender({ filter: 'true' })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]![0] as string
    expect(calledUrl).toContain('avaliada=true')
  })
})

// =============================================================================
// useConversationDetail
// =============================================================================

describe('useConversationDetail', () => {
  it('deve buscar detalhes de conversa', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'conv123',
          medico_nome: 'Dr. Carlos',
          interacoes: [
            {
              id: 'msg1',
              remetente: 'julia',
              conteudo: 'Oi!',
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    const { result } = renderHook(() => useConversationDetail('conv123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.conversation).not.toBeNull()
    expect(result.current.conversation?.id).toBe('conv123')
    expect(result.current.conversation?.mensagens).toHaveLength(1)
  })

  it('deve salvar avaliacao com sucesso', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            id: 'conv123',
            medico_nome: 'Dr. Carlos',
            interacoes: [],
          }),
      })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })

    const { result } = renderHook(() => useConversationDetail('conv123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.saveEvaluation(
        { naturalidade: 4, persona: 5, objetivo: 4, satisfacao: 4 },
        'Boa conversa'
      )
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/admin/avaliacoes',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      })
    )
  })

  it('deve tratar erro ao salvar avaliacao', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'conv123', interacoes: [] }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: 'Erro ao salvar' }),
      })

    const { result } = renderHook(() => useConversationDetail('conv123'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await expect(
      act(async () => {
        await result.current.saveEvaluation(
          { naturalidade: 4, persona: 5, objetivo: 4, satisfacao: 4 },
          'Boa conversa'
        )
      })
    ).rejects.toThrow('Erro ao salvar')
  })
})

// =============================================================================
// useSuggestions
// =============================================================================

describe('useSuggestions', () => {
  it('deve buscar sugestoes com filtro default', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          sugestoes: [
            {
              id: 'sug1',
              tipo: 'tom',
              descricao: 'Usar tom informal',
              status: 'pending',
              criada_em: '2024-01-15T10:00:00Z',
            },
          ],
        }),
    })

    const { result } = renderHook(() => useSuggestions())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.suggestions).toHaveLength(1)
    expect(result.current.suggestions[0]!.tipo).toBe('tom')
  })

  it('deve atualizar status de sugestao', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sugestoes: [] }),
      })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sugestoes: [] }),
      })

    const { result } = renderHook(() => useSuggestions())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.updateStatus('sug1', 'approved')
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/admin/sugestoes/sug1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ status: 'approved' }),
      })
    )
  })

  it('deve criar nova sugestao', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sugestoes: [] }),
      })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sugestoes: [] }),
      })

    const { result } = renderHook(() => useSuggestions())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.create({
        tipo: 'tom',
        descricao: 'Nova sugestao',
        exemplos: 'Exemplo',
      })
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/admin/sugestoes',
      expect.objectContaining({
        method: 'POST',
      })
    )
  })

  it('deve resetar actionLoading apos update', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sugestoes: [] }),
      })
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ sugestoes: [] }),
      })

    const { result } = renderHook(() => useSuggestions())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.actionLoading).toBeNull()

    await act(async () => {
      await result.current.updateStatus('sug1', 'approved')
    })

    // Apos completar, actionLoading deve ser null
    expect(result.current.actionLoading).toBeNull()
  })
})
