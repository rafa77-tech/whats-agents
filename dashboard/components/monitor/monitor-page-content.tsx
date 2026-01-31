/**
 * Monitor Page Content - Sprint 42
 *
 * Client component principal da pagina de monitor.
 * Gerencia estado, fetch de dados e auto-refresh.
 */

'use client'

import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { getMonitorOverview, getMonitorJobs } from '@/lib/api/monitor'
import {
  SystemHealthCard,
  JobsStatsCards,
  JobsFilters,
  JobsTable,
  JobDetailModal,
} from '@/components/monitor'
import { JOBS_BY_NAME } from '@/lib/monitor/jobs-config'
import type { MonitorOverviewResponse, MonitorJobsResponse, MonitorFilters } from '@/types/monitor'

/**
 * Converte nomes tecnicos de jobs para nomes amigaveis.
 */
function getJobDisplayNames(jobNames: string[]): string[] {
  return jobNames.map((name) => JOBS_BY_NAME[name]?.displayName ?? name)
}

const AUTO_REFRESH_INTERVAL = 30000 // 30 segundos

export function MonitorPageContent() {
  // Estado de dados
  const [overview, setOverview] = useState<MonitorOverviewResponse | null>(null)
  const [jobsData, setJobsData] = useState<MonitorJobsResponse | null>(null)

  // Estado de UI
  const [isLoading, setIsLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null)

  // Estado de filtros
  const [filters, setFilters] = useState<MonitorFilters>({
    status: 'all',
    timeRange: '24h',
    search: '',
    category: 'all',
  })

  // Estado do modal
  const [selectedJob, setSelectedJob] = useState<string | null>(null)
  const [isModalOpen, setIsModalOpen] = useState(false)

  // Fetch overview
  const fetchOverview = useCallback(async () => {
    try {
      const data = await getMonitorOverview()
      setOverview(data)
    } catch (error) {
      console.error('Error fetching overview:', error)
    }
  }, [])

  // Fetch jobs
  const fetchJobs = useCallback(async () => {
    try {
      const data = await getMonitorJobs({
        status: filters.status,
        timeRange: filters.timeRange,
        search: filters.search,
        category: filters.category,
      })
      setJobsData(data)
    } catch (error) {
      console.error('Error fetching jobs:', error)
    }
  }, [filters])

  // Fetch all data
  const fetchAll = useCallback(async () => {
    await Promise.all([fetchOverview(), fetchJobs()])
    setLastUpdate(new Date())
  }, [fetchOverview, fetchJobs])

  // Initial load
  useEffect(() => {
    const load = async () => {
      setIsLoading(true)
      await fetchAll()
      setIsLoading(false)
    }
    void load()
  }, [fetchAll])

  // Refetch jobs when filters change
  useEffect(() => {
    if (!isLoading) {
      void fetchJobs()
    }
  }, [filters, fetchJobs, isLoading])

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => {
      void fetchAll()
    }, AUTO_REFRESH_INTERVAL)
    return () => clearInterval(interval)
  }, [fetchAll])

  // Manual refresh
  const handleRefresh = async () => {
    setIsRefreshing(true)
    await fetchAll()
    setIsRefreshing(false)
  }

  // Open job detail modal
  const handleJobClick = (jobName: string) => {
    setSelectedJob(jobName)
    setIsModalOpen(true)
  }

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-6">
        <div className="h-8 w-48 rounded bg-gray-200" />
        <div className="h-32 rounded bg-gray-200" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 rounded bg-gray-200" />
          ))}
        </div>
        <div className="h-12 rounded bg-gray-200" />
        <div className="h-96 rounded bg-gray-200" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-bold text-gray-900">
            <Activity className="h-6 w-6" />
            Monitor do Sistema
          </h1>
          <p className="mt-1 text-sm text-gray-600">
            Monitoramento em tempo real dos jobs e saude do sistema
          </p>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-xs text-gray-500" suppressHydrationWarning>
              Atualizado: {lastUpdate.toLocaleTimeString('pt-BR')}
            </span>
          )}
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isRefreshing}>
            <RefreshCw className={cn('mr-2 h-4 w-4', isRefreshing && 'animate-spin')} />
            Atualizar
          </Button>
        </div>
      </div>

      {/* System Health */}
      <section aria-label="Saude do Sistema">
        <SystemHealthCard data={overview?.systemHealth ?? null} />
      </section>

      {/* Stats Cards */}
      <section aria-label="Estatisticas">
        <JobsStatsCards stats={overview?.jobsStats ?? null} />
      </section>

      {/* Alerts Banner (if any critical) */}
      {overview?.alerts.criticalStale.length ? (
        <section aria-label="Alertas">
          <div className="rounded-lg border border-red-200 bg-red-50 p-4">
            <div className="flex items-center gap-2 font-medium text-red-800">
              <Activity className="h-5 w-5" />
              {overview.alerts.criticalStale.length} job(s) critico(s) atrasado(s)
            </div>
            <div className="mt-2 text-sm text-red-700">
              {getJobDisplayNames(overview.alerts.criticalStale).join(', ')}
            </div>
          </div>
        </section>
      ) : null}

      {/* Filters */}
      <section aria-label="Filtros">
        <JobsFilters filters={filters} onFiltersChange={setFilters} />
      </section>

      {/* Jobs Table */}
      <section aria-label="Lista de Jobs">
        <JobsTable
          jobs={jobsData?.jobs ?? null}
          onJobClick={handleJobClick}
          onJobAction={handleRefresh}
        />
      </section>

      {/* Job Detail Modal */}
      <JobDetailModal open={isModalOpen} onOpenChange={setIsModalOpen} jobName={selectedJob} />
    </div>
  )
}
