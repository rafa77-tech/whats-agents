import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'
import {
  useDebounce,
  useGroupEntryDashboard,
  useLinksList,
  useProcessingQueue,
  useGroupEntryConfig,
  useLinkActions,
  useQueueActions,
  useBatchActions,
  useImportLinks,
} from '@/lib/group-entry/hooks'
import { DEFAULT_CONFIG } from '@/lib/group-entry/constants'

// Mock fetch globally
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('returns initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('test', 300))
    expect(result.current).toBe('test')
  })

  it('debounces value changes', () => {
    const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
      initialProps: { value: 'initial' },
    })

    expect(result.current).toBe('initial')

    rerender({ value: 'updated' })
    expect(result.current).toBe('initial')

    act(() => {
      vi.advanceTimersByTime(300)
    })
    expect(result.current).toBe('updated')
  })

  it('cancels previous timeout on rapid changes', () => {
    const { result, rerender } = renderHook(({ value }) => useDebounce(value, 300), {
      initialProps: { value: 'a' },
    })

    rerender({ value: 'b' })
    act(() => {
      vi.advanceTimersByTime(100)
    })

    rerender({ value: 'c' })
    act(() => {
      vi.advanceTimersByTime(100)
    })

    rerender({ value: 'd' })
    act(() => {
      vi.advanceTimersByTime(300)
    })

    expect(result.current).toBe('d')
  })
})

describe('useGroupEntryDashboard', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('fetches dashboard and capacity data on mount', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () =>
          Promise.resolve({
            links: { total: 100, pending: 10, validated: 20, scheduled: 30, processed: 40 },
            queue: { queued: 5, processing: 2 },
            processed_today: { success: 15, failed: 3 },
          }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ used: 50, total: 200 }),
      })

    const { result } = renderHook(() => useGroupEntryDashboard())

    expect(result.current.loading).toBe(true)

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).toEqual({
      links: { total: 100, pending: 10, validated: 20, scheduled: 30, processed: 40 },
      queue: { queued: 5, processing: 2 },
      processedToday: { success: 15, failed: 3 },
      capacity: { used: 50, total: 200 },
    })
  })

  it('handles partial API failures gracefully', async () => {
    mockFetch.mockResolvedValueOnce({ ok: false }).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ used: 25, total: 100 }),
    })

    const { result } = renderHook(() => useGroupEntryDashboard())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data?.capacity).toEqual({ used: 25, total: 100 })
    expect(result.current.data?.links.total).toBe(0)
  })

  it('provides refresh function', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({}),
    })

    const { result } = renderHook(() => useGroupEntryDashboard())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    await act(async () => {
      await result.current.refresh()
    })

    expect(mockFetch).toHaveBeenCalledTimes(2)
  })
})

describe('useLinksList', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('fetches links on mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          links: [
            {
              id: '1',
              url: 'https://test.com',
              status: 'pending',
              categoria: 'medicos',
              criado_em: '2024-01-01',
            },
          ],
          total: 1,
        }),
    })

    const { result } = renderHook(() => useLinksList())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.links).toHaveLength(1)
    expect(result.current.total).toBe(1)
  })

  it('applies status filter', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ links: [], total: 0 }),
    })

    renderHook(() => useLinksList({ status: 'pending' }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const url = mockFetch.mock.calls[0]?.[0] as string
    expect(url).toContain('status=pending')
  })

  it('applies search filter', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ links: [], total: 0 }),
    })

    renderHook(() => useLinksList({ search: 'test' }))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const url = mockFetch.mock.calls[0]?.[0] as string
    expect(url).toContain('search=test')
  })

  it('handles pagination', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ links: [], total: 50 }),
    })

    const { result } = renderHook(() => useLinksList())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.page).toBe(1)
    expect(result.current.totalPages).toBe(3) // 50/20 = 2.5 -> 3

    await act(async () => {
      result.current.setPage(2)
    })

    await waitFor(() => {
      const url = mockFetch.mock.calls[1]?.[0] as string
      expect(url).toContain('offset=20')
    })
  })

  it('handles fetch error', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useLinksList())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Erro ao buscar links')
    expect(result.current.links).toEqual([])
  })
})

describe('useProcessingQueue', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('fetches queue on mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          queue: [
            {
              id: '1',
              link_url: 'https://test.com',
              chip_name: 'Chip1',
              scheduled_at: '2024-01-01',
              status: 'queued',
            },
          ],
        }),
    })

    const { result } = renderHook(() => useProcessingQueue(false))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.queue).toHaveLength(1)
  })

  it('sets up auto-refresh when enabled', async () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval')
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ queue: [] }),
    })

    renderHook(() => useProcessingQueue(true))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    expect(setIntervalSpy).toHaveBeenCalled()
    setIntervalSpy.mockRestore()
  })

  it('does not auto-refresh when disabled', async () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval')
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ queue: [] }),
    })

    renderHook(() => useProcessingQueue(false))

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    // setInterval should not be called when autoRefresh is false
    const intervalCalls = setIntervalSpy.mock.calls.filter((call) => {
      // Check if the interval matches QUEUE_REFRESH_INTERVAL
      return call[1] === 30000
    })
    expect(intervalCalls).toHaveLength(0)
    setIntervalSpy.mockRestore()
  })

  it('handles fetch error', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useProcessingQueue(false))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Erro ao buscar fila')
    expect(result.current.queue).toEqual([])
  })
})

describe('useGroupEntryConfig', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('fetches config on mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          grupos_por_dia: 15,
          intervalo_min: 45,
          intervalo_max: 90,
          horario_inicio: '09:00',
          horario_fim: '18:00',
          dias_ativos: ['seg', 'ter'],
          auto_validar: true,
          auto_agendar: false,
          notificar_falhas: true,
        }),
    })

    const { result } = renderHook(() => useGroupEntryConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config.gruposPorDia).toBe(15)
    expect(result.current.config.autoValidar).toBe(true)
  })

  it('uses default config on fetch failure', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useGroupEntryConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.config).toEqual(DEFAULT_CONFIG)
  })

  it('saves config successfully', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ ok: true })

    const { result } = renderHook(() => useGroupEntryConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let success = false
    await act(async () => {
      success = await result.current.saveConfig({ ...DEFAULT_CONFIG, gruposPorDia: 20 })
    })

    expect(success).toBe(true)
    expect(result.current.config.gruposPorDia).toBe(20)
  })

  it('handles save error', async () => {
    mockFetch
      .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve({}) })
      .mockResolvedValueOnce({ ok: false })

    const { result } = renderHook(() => useGroupEntryConfig())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let success = false
    await act(async () => {
      success = await result.current.saveConfig(DEFAULT_CONFIG)
    })

    expect(success).toBe(false)
    expect(result.current.error).toBe('Erro ao salvar configuração')
  })
})

describe('useLinkActions', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('validates link successfully', async () => {
    mockFetch.mockResolvedValue({ ok: true })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useLinkActions(onSuccess))

    let success = false
    await act(async () => {
      success = await result.current.validateLink('link-123')
    })

    expect(success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/validate/link-123', { method: 'POST' })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('handles validate error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Link inválido' }),
    })

    const { result } = renderHook(() => useLinkActions())

    let success = false
    await act(async () => {
      success = await result.current.validateLink('link-123')
    })

    expect(success).toBe(false)
    expect(result.current.error).toBe('Link inválido')
  })

  it('schedules link successfully', async () => {
    mockFetch.mockResolvedValue({ ok: true })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useLinkActions(onSuccess))

    let success = false
    await act(async () => {
      success = await result.current.scheduleLink('link-456')
    })

    expect(success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ link_id: 'link-456' }),
    })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('clears error', async () => {
    mockFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })

    const { result } = renderHook(() => useLinkActions())

    await act(async () => {
      await result.current.validateLink('link-123')
    })

    expect(result.current.error).toBeTruthy()

    act(() => {
      result.current.clearError()
    })

    expect(result.current.error).toBe(null)
  })
})

describe('useQueueActions', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('processes item successfully', async () => {
    mockFetch.mockResolvedValue({ ok: true })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useQueueActions(onSuccess))

    let success = false
    await act(async () => {
      success = await result.current.processItem('queue-123')
    })

    expect(success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/process/queue-123', { method: 'POST' })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('cancels item successfully', async () => {
    mockFetch.mockResolvedValue({ ok: true })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useQueueActions(onSuccess))

    let success = false
    await act(async () => {
      success = await result.current.cancelItem('queue-456')
    })

    expect(success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/queue/queue-456', { method: 'DELETE' })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('handles process error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Item já processado' }),
    })

    const { result } = renderHook(() => useQueueActions())

    let success = false
    await act(async () => {
      success = await result.current.processItem('queue-123')
    })

    expect(success).toBe(false)
    expect(result.current.error).toBe('Item já processado')
  })

  it('handles cancel error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Não é possível cancelar' }),
    })

    const { result } = renderHook(() => useQueueActions())

    let success = false
    await act(async () => {
      success = await result.current.cancelItem('queue-456')
    })

    expect(success).toBe(false)
    expect(result.current.error).toBe('Não é possível cancelar')
  })
})

describe('useBatchActions', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('validates pending links', async () => {
    mockFetch.mockResolvedValue({ ok: true })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useBatchActions(onSuccess))

    let success = false
    await act(async () => {
      success = await result.current.validatePending()
    })

    expect(success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/validate/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'pending' }),
    })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('schedules validated links', async () => {
    mockFetch.mockResolvedValue({ ok: true })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useBatchActions(onSuccess))

    let success = false
    await act(async () => {
      success = await result.current.scheduleValidated()
    })

    expect(success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/schedule/batch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: 'validated' }),
    })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('processes queue', async () => {
    mockFetch.mockResolvedValue({ ok: true })
    const onSuccess = vi.fn()

    const { result } = renderHook(() => useBatchActions(onSuccess))

    let success = false
    await act(async () => {
      success = await result.current.processQueue()
    })

    expect(success).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/process', { method: 'POST' })
    expect(onSuccess).toHaveBeenCalled()
  })

  it('handles batch errors', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Sem links para validar' }),
    })

    const { result } = renderHook(() => useBatchActions())

    let success = false
    await act(async () => {
      success = await result.current.validatePending()
    })

    expect(success).toBe(false)
    expect(result.current.error).toBe('Sem links para validar')
  })

  it('clears error', async () => {
    mockFetch.mockResolvedValue({ ok: false, json: () => Promise.resolve({}) })

    const { result } = renderHook(() => useBatchActions())

    await act(async () => {
      await result.current.validatePending()
    })

    expect(result.current.error).toBeTruthy()

    act(() => {
      result.current.clearError()
    })

    expect(result.current.error).toBe(null)
  })
})

describe('useImportLinks', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  it('uploads file successfully', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          total: 100,
          valid: 90,
          duplicates: 5,
          invalid: 5,
          errors: [{ line: 10, error: 'URL inválida' }],
        }),
    })

    const { result } = renderHook(() => useImportLinks())

    const file = new File(['test'], 'test.csv', { type: 'text/csv' })

    let success = false
    await act(async () => {
      success = await result.current.uploadFile(file)
    })

    expect(success).toBe(true)
    expect(result.current.result).toEqual({
      total: 100,
      valid: 90,
      duplicates: 5,
      invalid: 5,
      errors: [{ line: 10, error: 'URL inválida' }],
    })
  })

  it('sends FormData with file', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total: 0, valid: 0, duplicates: 0, invalid: 0, errors: [] }),
    })

    const { result } = renderHook(() => useImportLinks())

    const file = new File(['content'], 'links.csv', { type: 'text/csv' })

    await act(async () => {
      await result.current.uploadFile(file)
    })

    expect(mockFetch).toHaveBeenCalledWith('/api/group-entry/import/csv', {
      method: 'POST',
      body: expect.any(FormData),
    })

    const formData = mockFetch.mock.calls[0]?.[1]?.body as FormData
    expect(formData.get('file')).toBe(file)
  })

  it('handles upload error', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      json: () => Promise.resolve({ error: 'Formato inválido' }),
    })

    const { result } = renderHook(() => useImportLinks())

    const file = new File(['test'], 'test.csv', { type: 'text/csv' })

    let success = false
    await act(async () => {
      success = await result.current.uploadFile(file)
    })

    expect(success).toBe(false)
    expect(result.current.error).toBe('Formato inválido')
    expect(result.current.result).toBe(null)
  })

  it('resets state', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ total: 10, valid: 10, duplicates: 0, invalid: 0, errors: [] }),
    })

    const { result } = renderHook(() => useImportLinks())

    const file = new File(['test'], 'test.csv', { type: 'text/csv' })

    await act(async () => {
      await result.current.uploadFile(file)
    })

    expect(result.current.result).not.toBe(null)

    act(() => {
      result.current.reset()
    })

    expect(result.current.result).toBe(null)
    expect(result.current.error).toBe(null)
  })

  it('initial state is correct', () => {
    const { result } = renderHook(() => useImportLinks())

    expect(result.current.uploading).toBe(false)
    expect(result.current.result).toBe(null)
    expect(result.current.error).toBe(null)
  })
})
