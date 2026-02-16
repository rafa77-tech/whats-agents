/**
 * Custom hooks for /vagas module
 */

'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { format, startOfMonth, endOfMonth, addMonths, subMonths } from 'date-fns'
import type { ShiftDetail, ShiftFilters, ShiftListResponse, Doctor, ViewMode } from './types'
import { PAGINATION } from './constants'

// =============================================================================
// API Endpoints
// =============================================================================

const API_ENDPOINTS = {
  shifts: '/api/vagas',
  shiftDetail: (id: string) => `/api/vagas/${id}`,
  doctors: '/api/medicos',
} as const

// =============================================================================
// Hook: useShifts
// =============================================================================

interface UseShiftsReturn {
  data: ShiftListResponse | null
  loading: boolean
  error: string | null
  filters: ShiftFilters
  search: string
  page: number
  viewMode: ViewMode
  calendarMonth: Date
  selectedDate: Date | undefined
  actions: {
    setFilters: (filters: ShiftFilters) => void
    setSearch: (search: string) => void
    setPage: (page: number) => void
    setViewMode: (mode: ViewMode) => void
    setCalendarMonth: (month: Date) => void
    handleDateSelect: (date: Date) => void
    handleCalendarMonthChange: (direction: 'prev' | 'next') => void
    clearFilters: () => void
    refresh: () => Promise<void>
  }
}

/**
 * Hook for managing shifts list page state and fetching
 */
export function useShifts(): UseShiftsReturn {
  const [data, setData] = useState<ShiftListResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<ShiftFilters>({})
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [viewMode, setViewMode] = useState<ViewMode>('list')
  const [calendarMonth, setCalendarMonth] = useState(new Date())
  const [selectedDate, setSelectedDate] = useState<Date | undefined>()

  const fetchShifts = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams()

      if (viewMode === 'calendar') {
        // For calendar, fetch all shifts for the visible month
        const monthStart = startOfMonth(calendarMonth)
        const monthEnd = endOfMonth(calendarMonth)
        params.set('date_from', format(monthStart, 'yyyy-MM-dd'))
        params.set('date_to', format(monthEnd, 'yyyy-MM-dd'))
        params.set('per_page', String(PAGINATION.CALENDAR_PAGE_SIZE))
      } else {
        // For list view, use pagination
        params.set('page', String(page))
        params.set('per_page', String(PAGINATION.DEFAULT_PAGE_SIZE))

        if (filters.date_from) params.set('date_from', filters.date_from)
        if (filters.date_to) params.set('date_to', filters.date_to)
      }

      if (filters.status) params.set('status', filters.status)
      if (filters.hospital_id) params.set('hospital_id', filters.hospital_id)
      if (filters.especialidade_id) params.set('especialidade_id', filters.especialidade_id)
      if (search) params.set('search', search)

      const response = await fetch(`${API_ENDPOINTS.shifts}?${params}`)

      if (response.ok) {
        const result = await response.json()
        setData(result)
      } else {
        setError('Erro ao carregar vagas')
      }
    } catch (err) {
      console.error('Failed to fetch shifts:', err)
      setError('Erro ao carregar vagas')
    } finally {
      setLoading(false)
    }
  }, [page, filters, search, viewMode, calendarMonth])

  useEffect(() => {
    fetchShifts()
  }, [fetchShifts])

  const handleSearch = useCallback((value: string) => {
    setSearch(value)
    setPage(1)
  }, [])

  const handleDateSelect = useCallback((date: Date) => {
    setSelectedDate(date)
    const dateStr = format(date, 'yyyy-MM-dd')
    setFilters((prev) => ({
      ...prev,
      date_from: dateStr,
      date_to: dateStr,
    }))
    setViewMode('list')
    setPage(1)
  }, [])

  const handleCalendarMonthChange = useCallback((direction: 'prev' | 'next') => {
    setCalendarMonth((prev) => (direction === 'next' ? addMonths(prev, 1) : subMonths(prev, 1)))
  }, [])

  const clearFilters = useCallback(() => {
    setFilters({})
    setSelectedDate(undefined)
    setPage(1)
  }, [])

  const handleSetFilters = useCallback((newFilters: ShiftFilters) => {
    setFilters(newFilters)
    setPage(1)
  }, [])

  return {
    data,
    loading,
    error,
    filters,
    search,
    page,
    viewMode,
    calendarMonth,
    selectedDate,
    actions: {
      setFilters: handleSetFilters,
      setSearch: handleSearch,
      setPage,
      setViewMode,
      setCalendarMonth,
      handleDateSelect,
      handleCalendarMonthChange,
      clearFilters,
      refresh: fetchShifts,
    },
  }
}

// =============================================================================
// Hook: useShiftDetail
// =============================================================================

interface UseShiftDetailReturn {
  shift: ShiftDetail | null
  loading: boolean
  error: string | null
  deleting: boolean
  assigning: boolean
  updating: boolean
  actions: {
    refresh: () => Promise<void>
    deleteShift: () => Promise<boolean>
    assignDoctor: (doctorId: string) => Promise<boolean>
    updateShift: (data: Record<string, unknown>) => Promise<boolean>
  }
}

/**
 * Hook for managing shift detail page state and actions
 */
export function useShiftDetail(id: string): UseShiftDetailReturn {
  const [shift, setShift] = useState<ShiftDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [assigning, setAssigning] = useState(false)
  const [updating, setUpdating] = useState(false)

  const fetchShift = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const response = await fetch(API_ENDPOINTS.shiftDetail(id))

      if (response.ok) {
        const data = await response.json()
        setShift(data)
      } else if (response.status === 404) {
        setError('Vaga nao encontrada')
      } else {
        setError('Erro ao carregar vaga')
      }
    } catch (err) {
      console.error('Failed to fetch shift:', err)
      setError('Erro ao carregar vaga')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    fetchShift()
  }, [fetchShift])

  const deleteShift = useCallback(async (): Promise<boolean> => {
    setDeleting(true)
    try {
      const response = await fetch(API_ENDPOINTS.shiftDetail(id), {
        method: 'DELETE',
      })

      if (response.ok) {
        return true
      } else {
        const data = await response.json()
        throw new Error(data.error || 'Erro ao excluir vaga')
      }
    } catch (err) {
      console.error('Failed to delete shift:', err)
      throw err
    } finally {
      setDeleting(false)
    }
  }, [id])

  const updateShift = useCallback(
    async (data: Record<string, unknown>): Promise<boolean> => {
      setUpdating(true)
      try {
        const response = await fetch(API_ENDPOINTS.shiftDetail(id), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        })

        if (response.ok) {
          await fetchShift()
          return true
        } else {
          const result = await response.json()
          throw new Error(result.error || 'Erro ao atualizar vaga')
        }
      } catch (err) {
        console.error('Failed to update shift:', err)
        throw err
      } finally {
        setUpdating(false)
      }
    },
    [id, fetchShift]
  )

  const assignDoctor = useCallback(
    async (doctorId: string): Promise<boolean> => {
      setAssigning(true)
      try {
        const response = await fetch(API_ENDPOINTS.shiftDetail(id), {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ cliente_id: doctorId }),
        })

        if (response.ok) {
          await fetchShift()
          return true
        } else {
          const data = await response.json()
          throw new Error(data.error || 'Erro ao atribuir medico')
        }
      } catch (err) {
        console.error('Failed to assign doctor:', err)
        throw err
      } finally {
        setAssigning(false)
      }
    },
    [id, fetchShift]
  )

  return {
    shift,
    loading,
    error,
    deleting,
    assigning,
    updating,
    actions: {
      refresh: fetchShift,
      deleteShift,
      assignDoctor,
      updateShift,
    },
  }
}

// =============================================================================
// Hook: useDoctorSearch
// =============================================================================

interface UseDoctorSearchReturn {
  search: string
  doctors: Doctor[]
  searching: boolean
  setSearch: (search: string) => void
  clear: () => void
}

/**
 * Hook for searching doctors with debounce
 */
export function useDoctorSearch(debounceMs: number = 300): UseDoctorSearchReturn {
  const [search, setSearch] = useState('')
  const [doctors, setDoctors] = useState<Doctor[]>([])
  const [searching, setSearching] = useState(false)
  const timerRef = useRef<NodeJS.Timeout | null>(null)

  useEffect(() => {
    // Clear previous timer
    if (timerRef.current) {
      clearTimeout(timerRef.current)
    }

    // Reset if search is too short
    if (!search || search.length < 2) {
      setDoctors([])
      return
    }

    // Debounce the search
    timerRef.current = setTimeout(async () => {
      setSearching(true)
      try {
        const response = await fetch(
          `${API_ENDPOINTS.doctors}?search=${encodeURIComponent(search)}&per_page=10`
        )
        if (response.ok) {
          const result = await response.json()
          setDoctors(result.data || [])
        }
      } catch (err) {
        console.error('Failed to search doctors:', err)
        setDoctors([])
      } finally {
        setSearching(false)
      }
    }, debounceMs)

    return () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current)
      }
    }
  }, [search, debounceMs])

  const clear = useCallback(() => {
    setSearch('')
    setDoctors([])
  }, [])

  return {
    search,
    doctors,
    searching,
    setSearch,
    clear,
  }
}
