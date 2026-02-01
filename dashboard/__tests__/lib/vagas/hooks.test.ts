/**
 * Testes para lib/vagas/hooks.ts
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor, act } from '@testing-library/react'
import { useShifts, useShiftDetail, useDoctorSearch } from '@/lib/vagas/hooks'

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
// useShifts
// =============================================================================

describe('useShifts', () => {
  it('deve iniciar com loading true', () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, pages: 0 }),
    })

    const { result } = renderHook(() => useShifts())

    expect(result.current.loading).toBe(true)
    expect(result.current.data).toBeNull()
  })

  it('deve buscar vagas no mount', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: [
            {
              id: 'v1',
              hospital: 'Hospital ABC',
              status: 'aberta',
            },
          ],
          total: 1,
          pages: 1,
        }),
    })

    const { result } = renderHook(() => useShifts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.data?.data).toHaveLength(1)
    expect(result.current.data?.data[0]?.hospital).toBe('Hospital ABC')
    expect(mockFetch).toHaveBeenCalledWith(expect.stringContaining('/api/vagas'))
  })

  it('deve refetch quando filtros mudam', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, pages: 0 }),
    })

    const { result } = renderHook(() => useShifts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    act(() => {
      result.current.actions.setFilters({ status: 'aberta' })
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]![0] as string
    expect(calledUrl).toContain('status=aberta')
  })

  it('deve resetar pagina ao buscar', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, pages: 0 }),
    })

    const { result } = renderHook(() => useShifts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Mudar para pagina 3
    act(() => {
      result.current.actions.setPage(3)
    })

    await waitFor(() => {
      expect(result.current.page).toBe(3)
    })

    // Buscar deve resetar para pagina 1
    act(() => {
      result.current.actions.setSearch('cardio')
    })

    expect(result.current.page).toBe(1)
  })

  it('deve funcionar em modo calendario', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, pages: 0 }),
    })

    const { result } = renderHook(() => useShifts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    mockFetch.mockClear()

    act(() => {
      result.current.actions.setViewMode('calendar')
    })

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled()
    })

    const calledUrl = mockFetch.mock.calls[0]![0] as string
    expect(calledUrl).toContain('date_from=')
    expect(calledUrl).toContain('date_to=')
    expect(calledUrl).toContain('per_page=500')
  })

  it('deve selecionar data do calendario', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, pages: 0 }),
    })

    const { result } = renderHook(() => useShifts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    // Use UTC date to avoid timezone issues
    const testDate = new Date('2024-01-15T12:00:00Z')

    act(() => {
      result.current.actions.handleDateSelect(testDate)
    })

    expect(result.current.selectedDate).toEqual(testDate)
    expect(result.current.viewMode).toBe('list')
    // Filters will use local date format, just check they're set
    expect(result.current.filters.date_from).toBeDefined()
    expect(result.current.filters.date_to).toBeDefined()
    expect(result.current.filters.date_from).toBe(result.current.filters.date_to)
  })

  it('deve limpar filtros', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [], total: 0, pages: 0 }),
    })

    const { result } = renderHook(() => useShifts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    act(() => {
      result.current.actions.setFilters({ status: 'aberta' })
      result.current.actions.setPage(3)
    })

    act(() => {
      result.current.actions.clearFilters()
    })

    expect(result.current.filters).toEqual({})
    expect(result.current.page).toBe(1)
    expect(result.current.selectedDate).toBeUndefined()
  })

  it('deve tratar erro de API', async () => {
    mockFetch.mockResolvedValue({ ok: false })

    const { result } = renderHook(() => useShifts())

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Erro ao carregar vagas')
  })
})

// =============================================================================
// useShiftDetail
// =============================================================================

describe('useShiftDetail', () => {
  it('deve buscar detalhes da vaga', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          id: 'v1',
          hospital: 'Hospital ABC',
          especialidade: 'Cardiologia',
          status: 'aberta',
        }),
    })

    const { result } = renderHook(() => useShiftDetail('v1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.shift?.id).toBe('v1')
    expect(result.current.shift?.hospital).toBe('Hospital ABC')
  })

  it('deve tratar erro 404', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
    })

    const { result } = renderHook(() => useShiftDetail('v1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    expect(result.current.error).toBe('Vaga nao encontrada')
    expect(result.current.shift).toBeNull()
  })

  it('deve deletar vaga', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'v1' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })

    const { result } = renderHook(() => useShiftDetail('v1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let deleteResult: boolean | undefined
    await act(async () => {
      deleteResult = await result.current.actions.deleteShift()
    })

    expect(deleteResult).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/vagas/v1',
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('deve atribuir medico', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'v1', status: 'aberta' }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'v1', status: 'reservada' }),
      })

    const { result } = renderHook(() => useShiftDetail('v1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    let assignResult: boolean | undefined
    await act(async () => {
      assignResult = await result.current.actions.assignDoctor('doctor-123')
    })

    expect(assignResult).toBe(true)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/vagas/v1',
      expect.objectContaining({
        method: 'PATCH',
        body: JSON.stringify({ cliente_id: 'doctor-123' }),
      })
    )
  })

  it('deve tratar erro ao deletar', async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'v1' }),
      })
      .mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ error: 'Erro ao excluir' }),
      })

    const { result } = renderHook(() => useShiftDetail('v1'))

    await waitFor(() => {
      expect(result.current.loading).toBe(false)
    })

    await expect(
      act(async () => {
        await result.current.actions.deleteShift()
      })
    ).rejects.toThrow('Erro ao excluir')
  })
})

// =============================================================================
// useDoctorSearch
// =============================================================================

describe('useDoctorSearch', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('deve fazer debounce da busca', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [] }),
    })

    const { result } = renderHook(() => useDoctorSearch(300))

    act(() => {
      result.current.setSearch('car')
    })

    // Antes do debounce
    expect(mockFetch).not.toHaveBeenCalled()

    // Apos o debounce
    await act(async () => {
      vi.advanceTimersByTime(300)
    })

    expect(mockFetch).toHaveBeenCalled()
    const calledUrl = mockFetch.mock.calls[0]![0] as string
    expect(calledUrl).toContain('search=car')
  })

  it('deve retornar vazio para queries curtas', async () => {
    const { result } = renderHook(() => useDoctorSearch())

    act(() => {
      result.current.setSearch('a')
    })

    await act(async () => {
      vi.advanceTimersByTime(500)
    })

    expect(mockFetch).not.toHaveBeenCalled()
    expect(result.current.doctors).toEqual([])
  })

  it('deve buscar medicos', async () => {
    const mockDoctors = [
      { id: 'd1', nome: 'Dr. Carlos', telefone: '11999999999' },
      { id: 'd2', nome: 'Dra. Carla', telefone: '11888888888' },
    ]

    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: mockDoctors }),
    })

    const { result } = renderHook(() => useDoctorSearch())

    act(() => {
      result.current.setSearch('carl')
    })

    await act(async () => {
      vi.advanceTimersByTime(300)
    })

    expect(result.current.doctors).toHaveLength(2)
    expect(result.current.doctors[0]?.nome).toBe('Dr. Carlos')
  })

  it('deve limpar busca', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          data: [{ id: 'd1', nome: 'Dr. Carlos', telefone: '11999999999' }],
        }),
    })

    const { result } = renderHook(() => useDoctorSearch())

    act(() => {
      result.current.setSearch('carlos')
    })

    await act(async () => {
      vi.advanceTimersByTime(300)
    })

    expect(result.current.doctors).toHaveLength(1)

    act(() => {
      result.current.clear()
    })

    expect(result.current.search).toBe('')
    expect(result.current.doctors).toEqual([])
  })

  it('deve cancelar timer anterior ao mudar busca', async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ data: [] }),
    })

    const { result } = renderHook(() => useDoctorSearch(300))

    act(() => {
      result.current.setSearch('car')
    })

    await act(async () => {
      vi.advanceTimersByTime(150) // Metade do debounce
    })

    act(() => {
      result.current.setSearch('carlos') // Nova busca
    })

    await act(async () => {
      vi.advanceTimersByTime(150) // Completa primeiro timer (mas foi cancelado)
    })

    expect(mockFetch).not.toHaveBeenCalled()

    await act(async () => {
      vi.advanceTimersByTime(150) // Completa segundo timer
    })

    expect(mockFetch).toHaveBeenCalledTimes(1)
    const calledUrl = mockFetch.mock.calls[0]![0] as string
    expect(calledUrl).toContain('search=carlos')
  })
})
