/**
 * API: GET /api/dashboard/monitor
 * Sprint 42 - Monitor Page
 *
 * Retorna overview do sistema incluindo:
 * - Saude do sistema
 * - Estatisticas agregadas dos jobs
 * - Alertas ativos
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { JOBS, TOTAL_JOBS, JOBS_BY_NAME } from '@/lib/monitor/jobs-config'
import type { MonitorOverviewResponse, SystemHealthStatus, JobStatus } from '@/types/monitor'

export const dynamic = 'force-dynamic'

interface FilaStats {
  pendentes: number
  processando: number
  travadas: number
  errosUltimaHora: number
  msgMaisAntiga: string | null
}

interface ChipsStats {
  criticalChips: number
  warningChips: number
  criticalAlerts: number
  warningAlerts: number
}

/**
 * Calcula score de saude da fila de mensagens.
 */
function calculateFilaScore(stats: FilaStats): { score: number; details: string } {
  let score = 100
  const issues: string[] = []

  // Penalidades por pendentes
  if (stats.pendentes > 500) {
    score -= 50
    issues.push('critical backlog')
  } else if (stats.pendentes > 100) {
    score -= 20
    issues.push('backlog elevado')
  }

  // Penalidades por mensagens travadas
  if (stats.travadas > 10) {
    score -= 30
    issues.push('muitas travadas')
  } else if (stats.travadas > 0) {
    score -= 10
    issues.push(`${stats.travadas} travada(s)`)
  }

  // Penalidades por erros recentes
  if (stats.errosUltimaHora > 10) {
    score -= 15
    issues.push('erros frequentes')
  } else if (stats.errosUltimaHora > 0) {
    score -= 5
  }

  // Penalidade por mensagem antiga
  if (stats.msgMaisAntiga) {
    const ageMinutes = (Date.now() - new Date(stats.msgMaisAntiga).getTime()) / 60000
    if (ageMinutes > 60) {
      score -= 10
      issues.push('msg antiga > 1h')
    }
  }

  score = Math.max(0, score)
  const details =
    issues.length > 0
      ? issues.join(', ')
      : `${stats.pendentes} pendentes, ${stats.processando} processando`

  return { score, details }
}

/**
 * Calcula score de saude do pool de chips.
 */
function calculateChipsScore(stats: ChipsStats): { score: number; details: string } {
  let score = 100
  const issues: string[] = []

  // Penalidades por chips com trust baixo
  score -= stats.criticalChips * 15
  score -= stats.warningChips * 5

  // Penalidades por alertas
  score -= stats.criticalAlerts * 10
  score -= stats.warningAlerts * 3

  score = Math.max(0, Math.min(100, score))

  if (stats.criticalChips > 0) issues.push(`${stats.criticalChips} critico(s)`)
  if (stats.criticalAlerts > 0) issues.push(`${stats.criticalAlerts} alerta(s) critico(s)`)

  const details = issues.length > 0 ? issues.join(', ') : 'Chips operacionais'

  return { score, details }
}

export async function GET() {
  try {
    const supabase = await createClient()
    const now = new Date()
    const twentyFourHoursAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)

    // Query: Estatisticas de jobs, fila e chips em paralelo
    const [executionsResult, filaResult, chipsResult, alertsResult] = await Promise.all([
      // Jobs nas ultimas 24h
      supabase
        .from('job_executions')
        .select('job_name, status, started_at, finished_at, duration_ms')
        .gte('started_at', twentyFourHoursAgo.toISOString())
        .order('started_at', { ascending: false }),

      // Estatisticas da fila de mensagens (RPC function)
      supabase.rpc('get_fila_stats'),

      // Chips para calcular trust scores
      supabase.from('chips').select('id, status, trust_score'),

      // Alertas ativos de chips
      supabase.from('chip_alerts').select('id, severity, tipo').eq('resolved', false),
    ])

    const { data: executions, error } = executionsResult

    // Processar estatisticas da fila
    const filaData = filaResult.data as {
      pendentes: number
      processando: number
      travadas: number
      errosUltimaHora: number
      msgMaisAntiga: string | null
    } | null

    const filaStats: FilaStats = {
      pendentes: filaData?.pendentes || 0,
      processando: filaData?.processando || 0,
      travadas: filaData?.travadas || 0,
      errosUltimaHora: filaData?.errosUltimaHora || 0,
      msgMaisAntiga: filaData?.msgMaisAntiga || null,
    }

    // Processar estatisticas de chips
    const chips = chipsResult.data || []
    const alerts = alertsResult.data || []

    const chipsStats: ChipsStats = {
      criticalChips: chips.filter((c) => (c.trust_score || 0) < 30).length,
      warningChips: chips.filter((c) => (c.trust_score || 0) >= 30 && (c.trust_score || 0) < 60)
        .length,
      criticalAlerts: alerts.filter((a) => a.severity === 'critico').length,
      warningAlerts: alerts.filter((a) => a.severity === 'alerta').length,
    }

    if (error) {
      console.error('Error fetching job executions:', error)
      throw error
    }

    // Agregar estatisticas por job
    const jobStats: Record<
      string,
      {
        runs: number
        success: number
        errors: number
        timeouts: number
        lastRun: string | null
        lastStatus: JobStatus | null
      }
    > = {}

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

    // Processar execucoes
    executions?.forEach((exec) => {
      const stats = jobStats[exec.job_name]
      if (!stats) return // Job desconhecido

      stats.runs++
      if (exec.status === 'success') stats.success++
      if (exec.status === 'error') stats.errors++
      if (exec.status === 'timeout') stats.timeouts++

      // Primeira execucao encontrada e a mais recente (ordenado desc)
      if (!stats.lastRun) {
        stats.lastRun = exec.started_at
        stats.lastStatus = exec.status as JobStatus
      }
    })

    // Calcular metricas globais
    let totalRuns = 0
    let totalSuccess = 0
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

      // Jobs com erros
      if (stats.errors > 0) {
        jobsWithErrors.push(jobName)
      }

      // Jobs com timeouts
      if (stats.timeouts > 0) {
        jobsWithTimeouts.push(jobName)
      }

      // Verificar se esta stale
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
        // Job critico que nunca executou
        missingCritical.push(jobName)
      }

      // Jobs running (status da ultima execucao)
      if (stats.lastStatus === 'running') {
        runningJobs++
      }
    })

    // Calcular taxa de sucesso
    const successRate24h = totalRuns > 0 ? Math.round((totalSuccess / totalRuns) * 100) : 100

    // Calcular saude da fila e chips (uma vez)
    const filaHealth = calculateFilaScore(filaStats)
    const chipsHealth = calculateChipsScore(chipsStats)

    // Determinar saude do sistema
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
            details:
              criticalStale.length === 0
                ? 'All systems connected'
                : `${criticalStale.length} critical jobs stale`,
          },
          fila: {
            score: filaHealth.score,
            max: 100,
            details: filaHealth.details,
          },
          chips: {
            score: chipsHealth.score,
            max: 100,
            details: chipsHealth.details,
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
    return NextResponse.json({ error: 'Failed to fetch monitor overview' }, { status: 500 })
  }
}
