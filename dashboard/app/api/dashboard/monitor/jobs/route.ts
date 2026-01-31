/**
 * API: GET /api/dashboard/monitor/jobs
 * Sprint 42 - Monitor Page
 *
 * Retorna lista de jobs com resumo e suporte a filtros.
 *
 * Query params:
 * - status: all | running | success | error | timeout | stale
 * - timeRange: 1h | 6h | 24h
 * - search: string (filtro por nome)
 * - category: all | critical | frequent | hourly | daily | weekly
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { JOBS } from '@/lib/monitor/jobs-config'
import { calculateNextRun, getCronDescription } from '@/lib/utils/cron-calculator'
import type {
  MonitorJobsResponse,
  JobSummary,
  JobStatus,
  JobStatusFilter,
  TimeRangeFilter,
  JobCategory,
} from '@/types/monitor'

export const dynamic = 'force-dynamic'

// Mapeia timeRange para milissegundos
const TIME_RANGE_MS: Record<TimeRangeFilter, number> = {
  '1h': 60 * 60 * 1000,
  '6h': 6 * 60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const statusFilter = (searchParams.get('status') || 'all') as JobStatusFilter
    const timeRange = (searchParams.get('timeRange') || '24h') as TimeRangeFilter
    const searchQuery = searchParams.get('search') || ''
    const categoryFilter = (searchParams.get('category') || 'all') as JobCategory | 'all'

    const supabase = await createClient()
    const now = new Date()
    const rangeStart = new Date(now.getTime() - TIME_RANGE_MS[timeRange])

    // Query execucoes no periodo (para estatisticas)
    const [executionsResult, lastExecutionsResult] = await Promise.all([
      // Estatisticas no periodo selecionado
      supabase
        .from('job_executions')
        .select('*')
        .gte('started_at', rangeStart.toISOString())
        .order('started_at', { ascending: false }),

      // Ultima execucao de cada job (sem filtro de tempo)
      supabase.rpc('get_last_job_executions'),
    ])

    const { data: executions, error } = executionsResult

    if (error) {
      console.error('Error fetching job executions:', error)
      throw error
    }

    // Mapear ultima execucao por job
    const lastExecByJob: Record<
      string,
      { started_at: string; status: string; error: string | null }
    > = {}
    if (lastExecutionsResult.data) {
      for (const exec of lastExecutionsResult.data as Array<{
        job_name: string
        started_at: string
        status: string
        error: string | null
      }>) {
        lastExecByJob[exec.job_name] = exec
      }
    }

    // Agregar por job
    const jobData: Record<
      string,
      {
        runs: number
        success: number
        errors: number
        timeouts: number
        totalDuration: number
        totalItems: number
        lastRun: string | null
        lastStatus: JobStatus | null
        lastError: string | null
      }
    > = {}

    // Inicializar todos os jobs
    JOBS.forEach((job) => {
      jobData[job.name] = {
        runs: 0,
        success: 0,
        errors: 0,
        timeouts: 0,
        totalDuration: 0,
        totalItems: 0,
        lastRun: null,
        lastStatus: null,
        lastError: null,
      }
    })

    // Processar execucoes
    executions?.forEach((exec) => {
      const data = jobData[exec.job_name]
      if (!data) return

      data.runs++
      if (exec.status === 'success') data.success++
      if (exec.status === 'error') data.errors++
      if (exec.status === 'timeout') data.timeouts++
      if (exec.duration_ms) data.totalDuration += exec.duration_ms
      if (exec.items_processed) data.totalItems += exec.items_processed

      if (!data.lastRun) {
        data.lastRun = exec.started_at
        data.lastStatus = exec.status as JobStatus
        if (exec.error) data.lastError = exec.error
      }
    })

    // Construir lista de JobSummary
    const jobs: JobSummary[] = JOBS.map((jobDef) => {
      const data = jobData[jobDef.name] || {
        runs: 0,
        success: 0,
        errors: 0,
        timeouts: 0,
        totalDuration: 0,
        totalItems: 0,
        lastRun: null,
        lastStatus: null,
        lastError: null,
      }

      // Usar ultima execucao real (sem filtro de tempo) para lastRun/lastStatus
      const lastExec = lastExecByJob[jobDef.name]
      const actualLastRun = lastExec?.started_at || null
      const actualLastStatus = lastExec?.status as JobStatus | null
      const actualLastError = lastExec?.error || null

      const secondsSinceLastRun = actualLastRun
        ? (now.getTime() - new Date(actualLastRun).getTime()) / 1000
        : null

      const isStale = secondsSinceLastRun ? secondsSinceLastRun > jobDef.slaSeconds : true // Nunca executou = stale

      return {
        name: jobDef.name,
        displayName: jobDef.displayName,
        category: jobDef.category,
        schedule: jobDef.schedule,
        scheduleDescription: getCronDescription(jobDef.schedule),
        description: jobDef.description,
        lastRun: actualLastRun,
        lastStatus: actualLastStatus,
        nextExpectedRun: calculateNextRun(jobDef.schedule),
        runs24h: data.runs,
        success24h: data.success,
        errors24h: data.errors,
        timeouts24h: data.timeouts,
        avgDurationMs: data.runs > 0 ? Math.round(data.totalDuration / data.runs) : 0,
        totalItemsProcessed: data.totalItems,
        lastError: actualLastError,
        slaSeconds: jobDef.slaSeconds,
        isStale,
        secondsSinceLastRun: secondsSinceLastRun ? Math.round(secondsSinceLastRun) : null,
        isCritical: jobDef.isCritical,
      }
    })

    // Aplicar filtros
    let filteredJobs = jobs

    // Filtro de status
    if (statusFilter !== 'all') {
      if (statusFilter === 'stale') {
        filteredJobs = filteredJobs.filter((j) => j.isStale)
      } else {
        filteredJobs = filteredJobs.filter((j) => j.lastStatus === statusFilter)
      }
    }

    // Filtro de categoria
    if (categoryFilter !== 'all') {
      filteredJobs = filteredJobs.filter((j) => j.category === categoryFilter)
    }

    // Filtro de busca
    if (searchQuery) {
      const query = searchQuery.toLowerCase()
      filteredJobs = filteredJobs.filter(
        (j) => j.name.toLowerCase().includes(query) || j.description.toLowerCase().includes(query)
      )
    }

    // Ordenar: criticos primeiro, depois por ultima execucao
    filteredJobs.sort((a, b) => {
      if (a.isCritical !== b.isCritical) {
        return a.isCritical ? -1 : 1
      }
      if (a.isStale !== b.isStale) {
        return a.isStale ? -1 : 1
      }
      if (!a.lastRun) return 1
      if (!b.lastRun) return -1
      return new Date(b.lastRun).getTime() - new Date(a.lastRun).getTime()
    })

    const response: MonitorJobsResponse = {
      jobs: filteredJobs,
      total: filteredJobs.length,
      period: timeRange,
      timestamp: now.toISOString(),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error in monitor jobs:', error)
    return NextResponse.json({ error: 'Failed to fetch monitor jobs' }, { status: 500 })
  }
}
