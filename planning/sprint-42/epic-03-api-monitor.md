# Epic 03: API Routes Monitor

## Objetivo

Criar 3 endpoints de API para a página Monitor que consultam a tabela `job_executions` do Supabase.

## Contexto

O dashboard precisa de APIs para:
1. Overview do sistema (saúde + stats)
2. Lista de jobs com resumo
3. Histórico de execuções de um job específico

### Estrutura de Arquivos

```
dashboard/app/api/dashboard/monitor/
├── route.ts                    # GET: Overview
├── jobs/
│   └── route.ts               # GET: Lista de jobs
└── job/
    └── [name]/
        └── executions/
            └── route.ts       # GET: Histórico
```

---

## Story 3.1: Criar API de Overview

### Objetivo
Implementar `GET /api/dashboard/monitor` que retorna saúde do sistema e estatísticas de jobs.

### Tarefas

1. **Criar estrutura de diretórios:**
```bash
mkdir -p dashboard/app/api/dashboard/monitor
```

2. **Implementar route.ts:**

**Arquivo:** `dashboard/app/api/dashboard/monitor/route.ts`

```typescript
/**
 * API: GET /api/dashboard/monitor
 * Sprint 42 - Monitor Page
 *
 * Retorna overview do sistema incluindo:
 * - Saúde do sistema
 * - Estatísticas agregadas dos jobs
 * - Alertas ativos
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { JOBS, CRITICAL_JOBS, TOTAL_JOBS, JOBS_BY_NAME } from '@/lib/monitor/jobs-config'
import type {
  MonitorOverviewResponse,
  SystemHealthStatus,
  JobStatus,
} from '@/types/monitor'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()
    const now = new Date()
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)

    // Query: Estatísticas de jobs nas últimas 24h
    const { data: executions, error } = await supabase
      .from('job_executions')
      .select('job_name, status, started_at, finished_at, duration_ms')
      .gte('started_at', twentyFourHoursAgo.toISOString())
      .order('started_at', { ascending: false })

    if (error) {
      console.error('Error fetching job executions:', error)
      throw error
    }

    // Agregar estatísticas por job
    const jobStats: Record<string, {
      runs: number
      success: number
      errors: number
      timeouts: number
      lastRun: string | null
      lastStatus: JobStatus | null
    }> = {}

    // Inicializar todos os jobs
    JOBS.forEach((job) => {
      jobStats[job.name] = {
        runs: 0,
        success: 0,
        errors: 0,
        timeouts: 0,
        lastRun: null,
        lastStatus: null,
      }
    })

    // Processar execuções
    executions?.forEach((exec) => {
      const stats = jobStats[exec.job_name]
      if (!stats) return // Job desconhecido

      stats.runs++
      if (exec.status === 'success') stats.success++
      if (exec.status === 'error') stats.errors++
      if (exec.status === 'timeout') stats.timeouts++

      // Primeira execução encontrada é a mais recente (ordenado desc)
      if (!stats.lastRun) {
        stats.lastRun = exec.started_at
        stats.lastStatus = exec.status as JobStatus
      }
    })

    // Calcular métricas globais
    let totalRuns = 0
    let totalSuccess = 0
    let totalErrors = 0
    let runningJobs = 0
    let staleJobs = 0
    const jobsWithErrors: string[] = []
    const jobsWithTimeouts: string[] = []
    const criticalStale: string[] = []
    const missingCritical: string[] = []

    Object.entries(jobStats).forEach(([jobName, stats]) => {
      const jobDef = JOBS_BY_NAME[jobName]
      if (!jobDef) return

      totalRuns += stats.runs
      totalSuccess += stats.success
      totalErrors += stats.errors

      // Jobs com erros
      if (stats.errors > 0) {
        jobsWithErrors.push(jobName)
      }

      // Jobs com timeouts
      if (stats.timeouts > 0) {
        jobsWithTimeouts.push(jobName)
      }

      // Verificar se está stale
      if (stats.lastRun) {
        const lastRunTime = new Date(stats.lastRun).getTime()
        const secondsSinceLastRun = (now.getTime() - lastRunTime) / 1000
        if (secondsSinceLastRun > jobDef.slaSeconds) {
          staleJobs++
          if (jobDef.isCritical) {
            criticalStale.push(jobName)
          }
        }
      } else if (jobDef.isCritical) {
        // Job crítico que nunca executou
        missingCritical.push(jobName)
      }

      // Jobs running (status da última execução)
      if (stats.lastStatus === 'running') {
        runningJobs++
      }
    })

    // Calcular taxa de sucesso
    const successRate24h = totalRuns > 0
      ? Math.round((totalSuccess / totalRuns) * 100)
      : 100

    // Determinar saúde do sistema
    let systemStatus: SystemHealthStatus = 'healthy'
    let healthScore = 100

    // Penalidades
    if (criticalStale.length > 0) {
      systemStatus = 'critical'
      healthScore -= 40
    }
    if (missingCritical.length > 0) {
      systemStatus = 'critical'
      healthScore -= 30
    }
    if (jobsWithErrors.length > 3) {
      systemStatus = systemStatus === 'critical' ? 'critical' : 'degraded'
      healthScore -= 20
    } else if (jobsWithErrors.length > 0) {
      healthScore -= jobsWithErrors.length * 5
    }
    if (staleJobs > 5) {
      systemStatus = systemStatus === 'critical' ? 'critical' : 'degraded'
      healthScore -= 10
    }

    healthScore = Math.max(0, healthScore)
    if (healthScore < 50 && systemStatus === 'healthy') {
      systemStatus = 'degraded'
    }

    // Construir resposta
    const response: MonitorOverviewResponse = {
      systemHealth: {
        status: systemStatus,
        score: healthScore,
        checks: {
          jobs: {
            score: Math.round(successRate24h),
            max: 100,
            details: `${successRate24h}% success rate`,
          },
          connectivity: {
            score: criticalStale.length === 0 ? 100 : 50,
            max: 100,
            details: criticalStale.length === 0 ? 'All systems connected' : `${criticalStale.length} critical jobs stale`,
          },
          fila: {
            score: 100, // TODO: Integrar com métricas reais de fila
            max: 100,
            details: 'Queue healthy',
          },
          chips: {
            score: 100, // TODO: Integrar com métricas reais de chips
            max: 100,
            details: 'Chips operational',
          },
        },
        lastUpdated: now.toISOString(),
      },
      jobsStats: {
        totalJobs: TOTAL_JOBS,
        successRate24h,
        failedJobs24h: jobsWithErrors.length,
        runningJobs,
        staleJobs,
      },
      alerts: {
        criticalStale,
        jobsWithErrors,
        jobsWithTimeouts,
        missingCritical,
      },
      timestamp: now.toISOString(),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error in monitor overview:', error)
    return NextResponse.json(
      { error: 'Failed to fetch monitor overview' },
      { status: 500 }
    )
  }
}
```

### DoD

- [ ] Endpoint `GET /api/dashboard/monitor` implementado
- [ ] Query job_executions últimas 24h
- [ ] Calcula successRate24h
- [ ] Identifica jobs stale
- [ ] Identifica jobs críticos com problema
- [ ] Retorna systemHealth com score
- [ ] Retorna jobsStats agregado
- [ ] Retorna alerts
- [ ] Error handling implementado

---

## Story 3.2: Criar API de Lista de Jobs

### Objetivo
Implementar `GET /api/dashboard/monitor/jobs` que retorna lista de jobs com filtros.

### Tarefas

1. **Criar estrutura:**
```bash
mkdir -p dashboard/app/api/dashboard/monitor/jobs
```

2. **Implementar route.ts:**

**Arquivo:** `dashboard/app/api/dashboard/monitor/jobs/route.ts`

```typescript
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
import { JOBS, JOBS_BY_NAME } from '@/lib/monitor/jobs-config'
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

    // Query execuções no período
    const { data: executions, error } = await supabase
      .from('job_executions')
      .select('*')
      .gte('started_at', rangeStart.toISOString())
      .order('started_at', { ascending: false })

    if (error) {
      console.error('Error fetching job executions:', error)
      throw error
    }

    // Agregar por job
    const jobData: Record<string, {
      runs: number
      success: number
      errors: number
      timeouts: number
      totalDuration: number
      totalItems: number
      lastRun: string | null
      lastStatus: JobStatus | null
      lastError: string | null
    }> = {}

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

    // Processar execuções
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
      const data = jobData[jobDef.name]
      const secondsSinceLastRun = data.lastRun
        ? (now.getTime() - new Date(data.lastRun).getTime()) / 1000
        : null

      const isStale = secondsSinceLastRun
        ? secondsSinceLastRun > jobDef.slaSeconds
        : true // Nunca executou = stale

      return {
        name: jobDef.name,
        category: jobDef.category,
        schedule: jobDef.schedule,
        description: jobDef.description,
        lastRun: data.lastRun,
        lastStatus: data.lastStatus,
        nextExpectedRun: null, // TODO: Calcular baseado no cron
        runs24h: data.runs,
        success24h: data.success,
        errors24h: data.errors,
        timeouts24h: data.timeouts,
        avgDurationMs: data.runs > 0 ? Math.round(data.totalDuration / data.runs) : 0,
        totalItemsProcessed: data.totalItems,
        lastError: data.lastError,
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
      filteredJobs = filteredJobs.filter((j) =>
        j.name.toLowerCase().includes(query) ||
        j.description.toLowerCase().includes(query)
      )
    }

    // Ordenar: críticos primeiro, depois por última execução
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
    return NextResponse.json(
      { error: 'Failed to fetch monitor jobs' },
      { status: 500 }
    )
  }
}
```

### DoD

- [ ] Endpoint `GET /api/dashboard/monitor/jobs` implementado
- [ ] Suporta filtro `status` (all, running, success, error, timeout, stale)
- [ ] Suporta filtro `timeRange` (1h, 6h, 24h)
- [ ] Suporta filtro `search` (busca por nome/descrição)
- [ ] Suporta filtro `category` (all, critical, frequent, hourly, daily, weekly)
- [ ] Calcula isStale baseado no SLA
- [ ] Ordena críticos primeiro, depois stale, depois recentes
- [ ] Retorna todos os campos de JobSummary
- [ ] Error handling implementado

---

## Story 3.3: Criar API de Histórico de Job

### Objetivo
Implementar `GET /api/dashboard/monitor/job/[name]/executions` que retorna histórico paginado.

### Tarefas

1. **Criar estrutura:**
```bash
mkdir -p dashboard/app/api/dashboard/monitor/job/[name]/executions
```

2. **Implementar route.ts:**

**Arquivo:** `dashboard/app/api/dashboard/monitor/job/[name]/executions/route.ts`

```typescript
/**
 * API: GET /api/dashboard/monitor/job/[name]/executions
 * Sprint 42 - Monitor Page
 *
 * Retorna histórico de execuções de um job específico com paginação.
 *
 * Path params:
 * - name: Nome do job
 *
 * Query params:
 * - page: Número da página (default: 1)
 * - pageSize: Itens por página (default: 20, max: 100)
 * - status: Filtro de status (opcional)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { JOBS_BY_NAME } from '@/lib/monitor/jobs-config'
import type { JobExecutionsResponse, JobExecution, JobStatus } from '@/types/monitor'

export const dynamic = 'force-dynamic'

interface RouteParams {
  params: Promise<{ name: string }>
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  try {
    const { name: jobName } = await params
    const searchParams = request.nextUrl.searchParams

    // Validar que o job existe
    if (!JOBS_BY_NAME[jobName]) {
      return NextResponse.json(
        { error: `Job not found: ${jobName}` },
        { status: 404 }
      )
    }

    // Parse query params
    const page = Math.max(1, parseInt(searchParams.get('page') || '1', 10))
    const pageSize = Math.min(100, Math.max(1, parseInt(searchParams.get('pageSize') || '20', 10)))
    const statusFilter = searchParams.get('status') as JobStatus | null

    const supabase = await createClient()
    const offset = (page - 1) * pageSize

    // Query com filtros
    let query = supabase
      .from('job_executions')
      .select('*', { count: 'exact' })
      .eq('job_name', jobName)
      .order('started_at', { ascending: false })

    if (statusFilter) {
      query = query.eq('status', statusFilter)
    }

    // Aplicar paginação
    query = query.range(offset, offset + pageSize - 1)

    const { data, error, count } = await query

    if (error) {
      console.error('Error fetching job executions:', error)
      throw error
    }

    // Mapear para tipo correto
    const executions: JobExecution[] = (data || []).map((row) => ({
      id: row.id,
      jobName: row.job_name,
      startedAt: row.started_at,
      finishedAt: row.finished_at,
      status: row.status as JobStatus,
      durationMs: row.duration_ms,
      responseCode: row.response_code,
      error: row.error,
      itemsProcessed: row.items_processed,
    }))

    const total = count || 0
    const hasMore = offset + executions.length < total

    const response: JobExecutionsResponse = {
      jobName,
      executions,
      total,
      page,
      pageSize,
      hasMore,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error in job executions:', error)
    return NextResponse.json(
      { error: 'Failed to fetch job executions' },
      { status: 500 }
    )
  }
}
```

### DoD

- [ ] Endpoint `GET /api/dashboard/monitor/job/[name]/executions` implementado
- [ ] Valida que o job existe (retorna 404 se não)
- [ ] Suporta paginação com `page` e `pageSize`
- [ ] Suporta filtro por `status`
- [ ] Retorna count total para paginação
- [ ] Retorna `hasMore` para navegação
- [ ] Ordena por started_at desc
- [ ] Mapeia campos para tipos corretos
- [ ] Error handling implementado

---

## Story 3.4: Criar Lib para API Client

### Objetivo
Criar funções de fetch no cliente para consumir as APIs.

### Tarefas

1. **Criar lib/api/monitor.ts:**

**Arquivo:** `dashboard/lib/api/monitor.ts`

```typescript
/**
 * Monitor API Client - Sprint 42
 *
 * Funções para consumir as APIs de monitor.
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
 * Busca overview do sistema (saúde + stats + alertas).
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
 * Busca histórico de execuções de um job.
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
```

### DoD

- [ ] Arquivo `lib/api/monitor.ts` criado
- [ ] Função `getMonitorOverview()` implementada
- [ ] Função `getMonitorJobs()` com suporte a todos os filtros
- [ ] Função `getJobExecutions()` com paginação
- [ ] Tipos corretos em todas as funções
- [ ] Error handling básico

---

## Checklist do Épico

- [ ] **S42.E03.1** - API `/api/dashboard/monitor` implementada
- [ ] **S42.E03.2** - API `/api/dashboard/monitor/jobs` implementada
- [ ] **S42.E03.3** - API `/api/dashboard/monitor/job/[name]/executions` implementada
- [ ] **S42.E03.4** - Client library `lib/api/monitor.ts` criada
- [ ] Todas as APIs respondem corretamente
- [ ] Error handling em todas as rotas
- [ ] Tipos TypeScript corretos

---

## Validação

```bash
cd dashboard

# Build para verificar tipos
npm run build

# Testar APIs manualmente (após iniciar dev server)
npm run dev

# Em outro terminal:
curl http://localhost:3000/api/dashboard/monitor | jq
curl "http://localhost:3000/api/dashboard/monitor/jobs?status=all&timeRange=24h" | jq
curl http://localhost:3000/api/dashboard/monitor/job/heartbeat/executions | jq
```
