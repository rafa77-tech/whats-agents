/**
 * Monitor API Client - Sprint 42
 *
 * Funcoes para consumir as APIs de monitor.
 */

import type {
  MonitorOverviewResponse,
  MonitorJobsResponse,
  JobExecutionsResponse,
  JobStatusFilter,
  TimeRangeFilter,
  JobCategory,
} from '@/types/monitor'

/**
 * Busca overview do sistema (saude + stats + alertas).
 */
export async function getMonitorOverview(): Promise<MonitorOverviewResponse> {
  const response = await fetch('/api/dashboard/monitor')
  if (!response.ok) {
    throw new Error('Failed to fetch monitor overview')
  }
  return response.json()
}

/**
 * Busca lista de jobs com filtros.
 */
export async function getMonitorJobs(params?: {
  status?: JobStatusFilter
  timeRange?: TimeRangeFilter
  search?: string
  category?: JobCategory | 'all'
}): Promise<MonitorJobsResponse> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.timeRange) searchParams.set('timeRange', params.timeRange)
  if (params?.search) searchParams.set('search', params.search)
  if (params?.category) searchParams.set('category', params.category)

  const url = `/api/dashboard/monitor/jobs${searchParams.toString() ? `?${searchParams}` : ''}`
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('Failed to fetch monitor jobs')
  }
  return response.json()
}

/**
 * Busca historico de execucoes de um job.
 */
export async function getJobExecutions(
  jobName: string,
  params?: {
    page?: number
    pageSize?: number
    status?: string
  }
): Promise<JobExecutionsResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.pageSize) searchParams.set('pageSize', params.pageSize.toString())
  if (params?.status) searchParams.set('status', params.status)

  const url = `/api/dashboard/monitor/job/${encodeURIComponent(jobName)}/executions${searchParams.toString() ? `?${searchParams}` : ''}`
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error('Failed to fetch job executions')
  }
  return response.json()
}
