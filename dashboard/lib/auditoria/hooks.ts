/**
 * Custom hooks para o modulo de Auditoria
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import type { AuditFilters, AuditResponse, UseAuditLogsReturn } from './types'
import { API_ENDPOINTS, DEFAULT_PER_PAGE, DEFAULT_FILTERS } from './constants'
import { buildAuditLogsUrl, buildExportUrl, formatDateForFilename } from './formatters'

// =============================================================================
// Hook: useAuditLogs
// =============================================================================

/**
 * Hook para gerenciar logs de auditoria
 */
export function useAuditLogs(): UseAuditLogsReturn {
  const [data, setData] = useState<AuditResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFiltersState] = useState<AuditFilters>({ ...DEFAULT_FILTERS })
  const [page, setPageState] = useState(1)
  const [searchInput, setSearchInput] = useState('')

  const fetchLogs = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const url = buildAuditLogsUrl(API_ENDPOINTS.logs, page, DEFAULT_PER_PAGE, filters)
      const response = await fetch(url)

      if (response.ok) {
        const result: AuditResponse = await response.json()
        setData(result)
      } else {
        setError('Erro ao carregar logs de auditoria')
      }
    } catch (err) {
      console.error('Failed to fetch audit logs:', err)
      setError('Erro ao carregar logs de auditoria')
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => {
    fetchLogs()
  }, [fetchLogs])

  const setFilters = useCallback((newFilters: AuditFilters) => {
    setFiltersState(newFilters)
    setPageState(1)
  }, [])

  const setPage = useCallback((newPage: number) => {
    setPageState(newPage)
  }, [])

  const setSearch = useCallback((value: string) => {
    setSearchInput(value)
    setFiltersState((prev) => ({
      ...prev,
      actor_email: value || undefined,
    }))
    setPageState(1)
  }, [])

  const clearFilters = useCallback(() => {
    setFiltersState({ ...DEFAULT_FILTERS })
    setSearchInput('')
    setPageState(1)
  }, [])

  const exportLogs = useCallback(async () => {
    try {
      const url = buildExportUrl(API_ENDPOINTS.export, filters)
      const response = await fetch(url)

      if (response.ok) {
        const blob = await response.blob()
        const blobUrl = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = blobUrl
        link.setAttribute('download', `audit_logs_${formatDateForFilename()}.csv`)
        document.body.appendChild(link)
        link.click()
        link.remove()
        window.URL.revokeObjectURL(blobUrl)
      } else {
        throw new Error('Erro ao exportar logs')
      }
    } catch (err) {
      console.error('Failed to export audit logs:', err)
      throw err
    }
  }, [filters])

  return {
    data,
    loading,
    error,
    filters,
    page,
    searchInput,
    actions: {
      setFilters,
      setPage,
      setSearch,
      clearFilters,
      refresh: fetchLogs,
      exportLogs,
    },
  }
}
