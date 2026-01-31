/**
 * API: GET /api/dashboard/monitor/job/[name]/executions
 * Sprint 42 - Monitor Page
 *
 * Retorna historico de execucoes de um job especifico com paginacao.
 *
 * Path params:
 * - name: Nome do job
 *
 * Query params:
 * - page: Numero da pagina (default: 1)
 * - pageSize: Itens por pagina (default: 20, max: 100)
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
      return NextResponse.json({ error: `Job not found: ${jobName}` }, { status: 404 })
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

    // Aplicar paginacao
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
    return NextResponse.json({ error: 'Failed to fetch job executions' }, { status: 500 })
  }
}
