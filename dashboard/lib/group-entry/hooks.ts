/**
 * Custom hooks para o módulo de Group Entry
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import type {
  GroupEntryDashboard,
  GroupLink,
  QueueItem,
  GroupEntryConfigUI,
  LinkFilters,
  ImportResult,
} from './types'
import { configApiToUI, configUIToApi } from './formatters'
import { DEFAULT_CONFIG, QUEUE_REFRESH_INTERVAL, DEFAULT_LINKS_LIMIT } from './constants'

/**
 * Hook para debounce de valores
 */
export function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(timer)
    }
  }, [value, delay])

  return debouncedValue
}

/**
 * Estado base para hooks de fetch
 */
interface FetchState<T> {
  data: T | null
  loading: boolean
  error: string | null
}

/**
 * Hook para buscar dados do dashboard
 */
export function useGroupEntryDashboard() {
  const [state, setState] = useState<FetchState<GroupEntryDashboard>>({
    data: null,
    loading: true,
    error: null,
  })

  const fetchData = useCallback(async () => {
    try {
      setState((prev) => ({ ...prev, loading: true, error: null }))

      const [dashboardRes, capacityRes] = await Promise.all([
        fetch('/api/group-entry/dashboard').catch(() => null),
        fetch('/api/group-entry/capacity').catch(() => null),
      ])

      let dashboardData = null
      if (dashboardRes?.ok) {
        dashboardData = await dashboardRes.json()
      }

      let capacityData = null
      if (capacityRes?.ok) {
        capacityData = await capacityRes.json()
      }

      setState({
        data: {
          links: {
            total: dashboardData?.links?.total || 0,
            pending: dashboardData?.links?.pending || 0,
            validated: dashboardData?.links?.validated || 0,
            scheduled: dashboardData?.links?.scheduled || 0,
            processed: dashboardData?.links?.processed || 0,
          },
          queue: {
            queued: dashboardData?.queue?.queued || 0,
            processing: dashboardData?.queue?.processing || 0,
          },
          processedToday: {
            success: dashboardData?.processed_today?.success || 0,
            failed: dashboardData?.processed_today?.failed || 0,
          },
          capacity: {
            used: capacityData?.used || 0,
            total: capacityData?.total || 100,
          },
        },
        loading: false,
        error: null,
      })
    } catch (err) {
      setState((prev) => ({
        ...prev,
        loading: false,
        error: err instanceof Error ? err.message : 'Erro ao carregar dados',
      }))
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  return {
    ...state,
    refresh: fetchData,
  }
}

/**
 * Hook para buscar lista de links com filtros e paginação
 */
export function useLinksList(filters: LinkFilters = {}) {
  const [links, setLinks] = useState<GroupLink[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)

  const limit = filters.limit || DEFAULT_LINKS_LIMIT

  const fetchLinks = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const params = new URLSearchParams()
      if (filters.status && filters.status !== 'all') {
        params.append('status', filters.status)
      }
      if (filters.search) {
        params.append('search', filters.search)
      }
      params.append('limit', String(limit))
      params.append('offset', String((page - 1) * limit))

      const res = await fetch(`/api/group-entry/links?${params.toString()}`)

      if (!res.ok) {
        throw new Error('Erro ao buscar links')
      }

      const data = await res.json()
      setLinks(
        data.links?.map((l: Record<string, unknown>) => ({
          id: l.id as string,
          url: l.url as string,
          status: l.status as string,
          categoria: l.categoria as string | null,
          criado_em: l.criado_em as string,
        })) || []
      )
      setTotal(data.total || data.links?.length || 0)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar links')
      setLinks([])
    } finally {
      setLoading(false)
    }
  }, [filters.status, filters.search, page, limit])

  useEffect(() => {
    fetchLinks()
  }, [fetchLinks])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [filters.status, filters.search])

  const totalPages = Math.ceil(total / limit)

  return {
    links,
    loading,
    error,
    total,
    page,
    totalPages,
    setPage,
    refresh: fetchLinks,
  }
}

/**
 * Hook para buscar fila de processamento com auto-refresh
 */
export function useProcessingQueue(autoRefresh = true) {
  const [queue, setQueue] = useState<QueueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)

  const fetchQueue = useCallback(async () => {
    try {
      setError(null)

      const res = await fetch('/api/group-entry/queue')

      if (!res.ok) {
        throw new Error('Erro ao buscar fila')
      }

      const data = await res.json()
      setQueue(
        data.queue?.map((q: Record<string, unknown>) => ({
          id: q.id as string,
          link_url: q.link_url as string,
          chip_name: q.chip_name as string,
          scheduled_at: q.scheduled_at as string,
          status: q.status as string,
        })) || []
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao buscar fila')
      setQueue([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchQueue()
  }, [fetchQueue])

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh) {
      intervalRef.current = setInterval(fetchQueue, QUEUE_REFRESH_INTERVAL)
      return () => {
        if (intervalRef.current) {
          clearInterval(intervalRef.current)
        }
      }
    }
    return undefined
  }, [autoRefresh, fetchQueue])

  return {
    queue,
    loading,
    error,
    refresh: fetchQueue,
  }
}

/**
 * Hook para gerenciar configuração
 */
export function useGroupEntryConfig() {
  const [config, setConfig] = useState<GroupEntryConfigUI>(DEFAULT_CONFIG)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchConfig = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const res = await fetch('/api/group-entry/config')

      if (res.ok) {
        const data = await res.json()
        setConfig(configApiToUI(data))
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar configuração')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConfig()
  }, [fetchConfig])

  const saveConfig = useCallback(async (newConfig: GroupEntryConfigUI): Promise<boolean> => {
    try {
      setSaving(true)
      setError(null)

      const res = await fetch('/api/group-entry/config', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(configUIToApi(newConfig)),
      })

      if (!res.ok) {
        throw new Error('Erro ao salvar configuração')
      }

      setConfig(newConfig)
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar configuração')
      return false
    } finally {
      setSaving(false)
    }
  }, [])

  return {
    config,
    setConfig,
    loading,
    saving,
    error,
    saveConfig,
    refresh: fetchConfig,
  }
}

/**
 * Hook para ações de links (validate, schedule)
 */
export function useLinkActions(onSuccess?: () => void) {
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const validateLink = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        setActionLoading(id)
        setError(null)

        const res = await fetch(`/api/group-entry/validate/${id}`, { method: 'POST' })

        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || 'Erro ao validar link')
        }

        onSuccess?.()
        return true
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao validar link')
        return false
      } finally {
        setActionLoading(null)
      }
    },
    [onSuccess]
  )

  const scheduleLink = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        setActionLoading(id)
        setError(null)

        const res = await fetch('/api/group-entry/schedule', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ link_id: id }),
        })

        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || 'Erro ao agendar link')
        }

        onSuccess?.()
        return true
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao agendar link')
        return false
      } finally {
        setActionLoading(null)
      }
    },
    [onSuccess]
  )

  return {
    actionLoading,
    error,
    clearError: () => setError(null),
    validateLink,
    scheduleLink,
  }
}

/**
 * Hook para ações da fila (process, cancel)
 */
export function useQueueActions(onSuccess?: () => void) {
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const processItem = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        setActionLoading(id)
        setError(null)

        const res = await fetch(`/api/group-entry/process/${id}`, { method: 'POST' })

        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || 'Erro ao processar item')
        }

        onSuccess?.()
        return true
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao processar item')
        return false
      } finally {
        setActionLoading(null)
      }
    },
    [onSuccess]
  )

  const cancelItem = useCallback(
    async (id: string): Promise<boolean> => {
      try {
        setActionLoading(id)
        setError(null)

        const res = await fetch(`/api/group-entry/queue/${id}`, { method: 'DELETE' })

        if (!res.ok) {
          const data = await res.json().catch(() => ({}))
          throw new Error(data.error || 'Erro ao cancelar item')
        }

        onSuccess?.()
        return true
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Erro ao cancelar item')
        return false
      } finally {
        setActionLoading(null)
      }
    },
    [onSuccess]
  )

  return {
    actionLoading,
    error,
    clearError: () => setError(null),
    processItem,
    cancelItem,
  }
}

/**
 * Hook para ações em lote
 */
export function useBatchActions(onSuccess?: () => void) {
  const [processingAction, setProcessingAction] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const validatePending = useCallback(async (): Promise<boolean> => {
    try {
      setProcessingAction('validate')
      setError(null)

      const res = await fetch('/api/group-entry/validate/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'pending' }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Erro ao validar links')
      }

      onSuccess?.()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao validar links')
      return false
    } finally {
      setProcessingAction(null)
    }
  }, [onSuccess])

  const scheduleValidated = useCallback(async (): Promise<boolean> => {
    try {
      setProcessingAction('schedule')
      setError(null)

      const res = await fetch('/api/group-entry/schedule/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'validated' }),
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Erro ao agendar links')
      }

      onSuccess?.()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao agendar links')
      return false
    } finally {
      setProcessingAction(null)
    }
  }, [onSuccess])

  const processQueue = useCallback(async (): Promise<boolean> => {
    try {
      setProcessingAction('process')
      setError(null)

      const res = await fetch('/api/group-entry/process', { method: 'POST' })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Erro ao processar fila')
      }

      onSuccess?.()
      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao processar fila')
      return false
    } finally {
      setProcessingAction(null)
    }
  }, [onSuccess])

  return {
    processingAction,
    error,
    clearError: () => setError(null),
    validatePending,
    scheduleValidated,
    processQueue,
  }
}

/**
 * Hook para importação de CSV
 */
export function useImportLinks() {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  const uploadFile = useCallback(async (file: File): Promise<boolean> => {
    try {
      setUploading(true)
      setError(null)
      setResult(null)

      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/group-entry/import/csv', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.error || 'Erro ao importar arquivo')
      }

      const data = await res.json()
      setResult({
        total: data.total || 0,
        valid: data.valid || 0,
        duplicates: data.duplicates || 0,
        invalid: data.invalid || 0,
        errors: data.errors || [],
      })

      return true
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao importar arquivo')
      return false
    } finally {
      setUploading(false)
    }
  }, [])

  const reset = useCallback(() => {
    setResult(null)
    setError(null)
  }, [])

  return {
    uploading,
    result,
    error,
    uploadFile,
    reset,
  }
}
