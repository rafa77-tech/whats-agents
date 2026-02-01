import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import {
  useIntegridadeData,
  parseKpisResponse,
  parseAnomaliasResponse,
} from '@/lib/integridade/hooks'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('parseKpisResponse', () => {
  it('parses flat structure', () => {
    const data = {
      health_score: 85,
      conversion_rate: 72,
      time_to_fill: 4.2,
    }

    const result = parseKpisResponse(data)

    expect(result.healthScore).toBe(85)
    expect(result.conversionRate).toBe(72)
    expect(result.timeToFill).toBe(4.2)
  })

  it('parses nested kpis structure', () => {
    const data = {
      kpis: {
        health_score: {
          score: 90,
          component_scores: {
            pressao: 2,
            friccao: 1,
            qualidade: 0.5,
            spam: 0,
          },
          recommendations: ['Recomendacao 1'],
        },
        conversion_rate: {
          value: 35,
        },
        time_to_fill: {
          time_to_fill_full: {
            avg_hours: 3.5,
          },
        },
      },
    }

    const result = parseKpisResponse(data)

    expect(result.healthScore).toBe(90)
    expect(result.conversionRate).toBe(35)
    expect(result.timeToFill).toBe(3.5)
    expect(result.componentScores.pressao).toBe(2)
    expect(result.componentScores.friccao).toBe(1)
    expect(result.componentScores.qualidade).toBe(0.5)
    expect(result.componentScores.spam).toBe(0)
    expect(result.recommendations).toEqual(['Recomendacao 1'])
  })

  it('handles missing data with defaults', () => {
    const data = {}

    const result = parseKpisResponse(data)

    expect(result.healthScore).toBe(0)
    expect(result.conversionRate).toBe(0)
    expect(result.timeToFill).toBe(0)
    expect(result.componentScores.pressao).toBe(0)
    expect(result.recommendations).toEqual([])
  })

  it('handles partial nested structure', () => {
    const data = {
      kpis: {
        health_score: {
          score: 75,
        },
      },
    }

    const result = parseKpisResponse(data)

    expect(result.healthScore).toBe(75)
    expect(result.conversionRate).toBe(0)
    expect(result.componentScores.pressao).toBe(0)
  })
})

describe('parseAnomaliasResponse', () => {
  it('parses anomalies array with Portuguese keys', () => {
    const data = {
      anomalias: [
        {
          id: '123',
          tipo: 'duplicata',
          entidade: 'medico',
          entidade_id: 'med-1',
          severidade: 'high',
          mensagem: 'Duplicado',
          criada_em: '2026-01-15T10:00:00Z',
          resolvida: false,
        },
      ],
    }

    const result = parseAnomaliasResponse(data)

    expect(result.anomaliasList).toHaveLength(1)
    expect(result.anomaliasList[0]?.id).toBe('123')
    expect(result.anomaliasList[0]?.tipo).toBe('duplicata')
    expect(result.anomaliasList[0]?.entidade).toBe('medico')
    expect(result.anomaliasList[0]?.entidadeId).toBe('med-1')
    expect(result.anomaliasList[0]?.severidade).toBe('high')
    expect(result.anomalias.abertas).toBe(1)
  })

  it('parses anomalies array with English keys', () => {
    const data = {
      anomalies: [
        {
          id: '456',
          type: 'missing_data',
          entity: 'vaga',
          entity_id: 'vag-1',
          severity: 'medium',
          message: 'Missing field',
          created_at: '2026-01-15T10:00:00Z',
          resolved: true,
        },
      ],
    }

    const result = parseAnomaliasResponse(data)

    expect(result.anomaliasList).toHaveLength(1)
    expect(result.anomaliasList[0]?.tipo).toBe('missing_data')
    expect(result.anomaliasList[0]?.entidade).toBe('vaga')
    expect(result.anomaliasList[0]?.entidadeId).toBe('vag-1')
    expect(result.anomaliasList[0]?.resolvida).toBe(true)
    expect(result.anomalias.resolvidas).toBe(1)
    expect(result.anomalias.abertas).toBe(0)
  })

  it('uses summary from backend when available', () => {
    const data = {
      anomalies: [
        { id: '1', resolvida: false },
        { id: '2', resolvida: false },
      ],
      summary: {
        total: 10,
        by_severity: {
          warning: 3,
          critical: 2,
        },
      },
    }

    const result = parseAnomaliasResponse(data)

    expect(result.anomalias.total).toBe(10)
    expect(result.anomalias.abertas).toBe(5) // 3 + 2
  })

  it('handles empty array', () => {
    const data = {
      anomalies: [],
    }

    const result = parseAnomaliasResponse(data)

    expect(result.anomaliasList).toHaveLength(0)
    expect(result.anomalias.abertas).toBe(0)
    expect(result.anomalias.resolvidas).toBe(0)
    expect(result.anomalias.total).toBe(0)
  })

  it('handles missing data', () => {
    const data = {}

    const result = parseAnomaliasResponse(data)

    expect(result.anomaliasList).toHaveLength(0)
    expect(result.anomalias.total).toBe(0)
  })
})

describe('useIntegridadeData', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('fetches data on mount', async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes('/kpis')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ health_score: 85, conversion_rate: 72, time_to_fill: 4 }),
        })
      }
      if (url.includes('/anomalias')) {
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              anomalies: [{ id: '1', tipo: 'test', severidade: 'low', resolvida: false }],
            }),
        })
      }
      return Promise.reject(new Error('Unknown URL'))
    })

    const { result } = renderHook(() => useIntegridadeData())

    // Initially loading
    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).not.toBeNull()
    expect(result.current.data?.kpis.healthScore).toBe(85)
    expect(result.current.data?.anomaliasList).toHaveLength(1)
    expect(result.current.error).toBeNull()
  })

  it('handles API errors gracefully with defaults', async () => {
    // Individual fetch errors are caught and return null, hook uses defaults
    mockFetch.mockImplementation(() => Promise.resolve(null))

    const { result } = renderHook(() => useIntegridadeData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Hook should still have data (defaults) since individual fetch errors are handled
    expect(result.current.data).not.toBeNull()
    expect(result.current.data?.kpis.healthScore).toBe(0)
  })

  it('handles failed API responses with defaults', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
    })

    const { result } = renderHook(() => useIntegridadeData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Should still have data (defaults)
    expect(result.current.data).not.toBeNull()
    expect(result.current.data?.kpis.healthScore).toBe(0)
    expect(result.current.data?.anomaliasList).toHaveLength(0)
  })

  it('runAudit triggers reconciliation and refetches', async () => {
    let callCount = 0
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === 'POST' && url.includes('/reconciliacao')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        })
      }
      callCount++
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            url.includes('/kpis')
              ? { health_score: callCount * 10 }
              : { anomalies: [] }
          ),
      })
    })

    const { result } = renderHook(() => useIntegridadeData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialScore = result.current.data?.kpis.healthScore

    await act(async () => {
      await result.current.runAudit()
    })

    // Should have refetched
    expect(result.current.data?.kpis.healthScore).not.toBe(initialScore)
    expect(mockFetch).toHaveBeenCalledWith('/api/integridade/reconciliacao', { method: 'POST' })
  })

  it('resolveAnomaly posts and refetches', async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === 'POST' && url.includes('/resolver')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ success: true }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(
            url.includes('/kpis') ? { health_score: 85 } : { anomalies: [] }
          ),
      })
    })

    const { result } = renderHook(() => useIntegridadeData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.resolveAnomaly('anomaly-123', '[Corrigido] Fixed')
    })

    expect(mockFetch).toHaveBeenCalledWith(
      '/api/integridade/anomalias/anomaly-123/resolver',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ notas: '[Corrigido] Fixed', usuario: 'dashboard' }),
      })
    )
  })

  it('sets error when runAudit fails', async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === 'POST' && url.includes('/reconciliacao')) {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ error: 'Audit failed' }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(url.includes('/kpis') ? { health_score: 85 } : { anomalies: [] }),
      })
    })

    const { result } = renderHook(() => useIntegridadeData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.runAudit()
    })

    expect(result.current.error).toBe('Audit failed')
  })

  it('throws error when resolveAnomaly fails', async () => {
    mockFetch.mockImplementation((url: string, options?: RequestInit) => {
      if (options?.method === 'POST' && url.includes('/resolver')) {
        return Promise.resolve({
          ok: false,
          json: () => Promise.resolve({ error: 'Resolve failed' }),
        })
      }
      return Promise.resolve({
        ok: true,
        json: () =>
          Promise.resolve(url.includes('/kpis') ? { health_score: 85 } : { anomalies: [] }),
      })
    })

    const { result } = renderHook(() => useIntegridadeData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // resolveAnomaly should throw the error
    await expect(
      act(async () => {
        await result.current.resolveAnomaly('anomaly-123', 'test')
      })
    ).rejects.toThrow('Resolve failed')
  })

  it('fetchData can be called manually', async () => {
    let fetchCount = 0
    mockFetch.mockImplementation(() => {
      fetchCount++
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ health_score: fetchCount * 10 }),
      })
    })

    const { result } = renderHook(() => useIntegridadeData())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    const initialCount = fetchCount

    await act(async () => {
      await result.current.fetchData()
    })

    expect(fetchCount).toBeGreaterThan(initialCount)
  })
})
