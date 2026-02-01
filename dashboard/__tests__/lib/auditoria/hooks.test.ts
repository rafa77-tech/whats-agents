/**
 * Testes para lib/auditoria/hooks.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useAuditLogs } from '@/lib/auditoria/hooks'

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
// useAuditLogs
// =============================================================================

describe('useAuditLogs', () => {
  const mockResponse = {
    data: [
      {
        id: 'log1',
        action: 'julia_toggle',
        actor_email: 'admin@example.com',
        actor_role: 'admin',
        details: { enabled: true },
        created_at: '2024-01-15T10:00:00Z',
      },
    ],
    total: 1,
    page: 1,
    per_page: 50,
    pages: 1,
  }

  it('deve iniciar com loading true', () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const { result } = renderHook(() => useAuditLogs())

    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
  })

  it('deve buscar logs no mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data).not.toBeNull()
    expect(result.current.data?.data).toHaveLength(1)
    expect(result.current.data?.data[0]?.action).toBe('julia_toggle')
  })

  it('deve chamar API com URL correta', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('/api/auditoria')
    expect(calledUrl).toContain('page=1')
    expect(calledUrl).toContain('per_page=50')
  })

  it('deve aplicar filtros', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    act(() => {
      result.current.actions.setFilters({ action: 'manual_handoff' })
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('action=manual_handoff')
  })

  it('deve resetar pagina ao aplicar filtros', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.actions.setPage(3)
    })

    expect(result.current.page).toBe(3)

    act(() => {
      result.current.actions.setFilters({ action: 'circuit_reset' })
    })

    expect(result.current.page).toBe(1)
  })

  it('deve atualizar busca e filtro de email', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    act(() => {
      result.current.actions.setSearch('admin@')
    })

    expect(result.current.searchInput).toBe('admin@')
    expect(result.current.filters.actor_email).toBe('admin@')

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('actor_email=admin%40')
  })

  it('deve limpar filtros', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.actions.setFilters({ action: 'julia_pause' })
      result.current.actions.setSearch('test@')
      result.current.actions.setPage(5)
    })

    act(() => {
      result.current.actions.clearFilters()
    })

    expect(result.current.filters.action).toBeUndefined()
    expect(result.current.filters.actor_email).toBeUndefined()
    expect(result.current.searchInput).toBe('')
    expect(result.current.page).toBe(1)
  })

  it('deve tratar erro de API', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Erro ao carregar logs de auditoria')
  })

  it('deve tratar erro de rede', async () => {
    mockFetch.mockRejectedValue(new Error('Network error'))

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Erro ao carregar logs de auditoria')
  })

  it('deve permitir refresh manual', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    await act(async () => {
      await result.current.actions.refresh()
    })

    expect(mockFetch).toHaveBeenCalled()
  })

  it('deve mudar de pagina', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ ...mockResponse, pages: 5 }),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    act(() => {
      result.current.actions.setPage(2)
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('page=2')
  })
})

// =============================================================================
// useAuditLogs - exportLogs
// =============================================================================

describe('useAuditLogs - exportLogs', () => {
  let originalCreateObjectURL: typeof URL.createObjectURL
  let originalRevokeObjectURL: typeof URL.revokeObjectURL
  let originalCreateElement: typeof document.createElement
  let originalAppendChild: typeof document.body.appendChild

  const mockLink = {
    href: '',
    download: '',
    setAttribute: vi.fn(),
    click: vi.fn(),
    remove: vi.fn(),
  }

  beforeEach(() => {
    // Save originals
    originalCreateObjectURL = URL.createObjectURL
    originalRevokeObjectURL = URL.revokeObjectURL
    originalCreateElement = document.createElement.bind(document)
    originalAppendChild = document.body.appendChild.bind(document.body)

    // Mock URL methods
    URL.createObjectURL = vi.fn(() => 'blob:test')
    URL.revokeObjectURL = vi.fn()

    // Mock document.createElement only for anchor elements
    document.createElement = vi.fn((tagName: string) => {
      if (tagName === 'a') {
        // Reset mock link state
        mockLink.href = ''
        mockLink.download = ''
        mockLink.setAttribute.mockClear()
        mockLink.click.mockClear()
        mockLink.remove.mockClear()
        return mockLink as unknown as HTMLAnchorElement
      }
      return originalCreateElement(tagName)
    }) as typeof document.createElement

    // Mock appendChild to accept our mock link
    document.body.appendChild = vi.fn((node) => {
      if (node === mockLink) {
        return node as Node
      }
      return originalAppendChild(node)
    }) as typeof document.body.appendChild
  })

  afterEach(() => {
    // Restore originals
    URL.createObjectURL = originalCreateObjectURL
    URL.revokeObjectURL = originalRevokeObjectURL
    document.createElement = originalCreateElement
    document.body.appendChild = originalAppendChild
  })

  it('deve exportar logs com sucesso', async () => {
    const mockBlob = new Blob(['csv data'], { type: 'text/csv' })

    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: [], total: 0, page: 1, per_page: 50, pages: 0 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        blob: () => Promise.resolve(mockBlob),
      })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await act(async () => {
      await result.current.actions.exportLogs()
    })

    // Verifica que a URL de export foi chamada
    const exportCall = mockFetch.mock.calls.find((call) =>
      (call[0] as string).includes('/api/auditoria/export')
    )
    expect(exportCall).toBeDefined()
  })

  it('deve incluir filtros na URL de export', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, page: 1, per_page: 50, pages: 0 }),
      blob: () => Promise.resolve(new Blob(['csv'], { type: 'text/csv' })),
    })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.actions.setFilters({ action: 'create_campaign', from_date: '2024-01-01' })
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    mockFetch.mockClear()

    await act(async () => {
      await result.current.actions.exportLogs()
    })

    const calledUrl = mockFetch.mock.calls[0]?.[0] as string
    expect(calledUrl).toContain('action=create_campaign')
    expect(calledUrl).toContain('from_date=2024-01-01')
  })

  it('deve lancar erro quando export falha', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: [], total: 0, page: 1, per_page: 50, pages: 0 }),
      })
      .mockResolvedValueOnce({
        ok: false,
      })

    const { result } = renderHook(() => useAuditLogs())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await expect(
      act(async () => {
        await result.current.actions.exportLogs()
      })
    ).rejects.toThrow('Erro ao exportar logs')
  })
})
