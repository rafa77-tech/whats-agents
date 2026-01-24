/**
 * API: GET /api/dashboard/chips/health
 *
 * Retorna status de saúde do pool de chips.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { PoolHealthStatus, PoolHealthIssue } from '@/types/chips'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    // Buscar chips e alertas em paralelo
    const [chipsResult, alertsResult] = await Promise.all([
      supabase.from('chips').select('id, status, trust_score'),
      supabase.from('chip_alerts').select('id, severity, tipo').eq('resolved', false),
    ])

    const chips = chipsResult.data || []
    const alerts = alertsResult.data || []

    // Calcular métricas
    const criticalChips = chips.filter((c) => (c.trust_score || 0) < 30).length
    const warningChips = chips.filter(
      (c) => (c.trust_score || 0) >= 30 && (c.trust_score || 0) < 60
    ).length
    const criticalAlerts = alerts.filter((a) => a.severity === 'critico').length
    const warningAlerts = alerts.filter((a) => a.severity === 'alerta').length

    // Calcular score de saúde
    let score = 100
    score -= criticalChips * 15
    score -= warningChips * 5
    score -= criticalAlerts * 10
    score -= warningAlerts * 3
    score = Math.max(0, Math.min(100, score))

    // Determinar status
    let status: PoolHealthStatus['status'] = 'healthy'
    if (score < 50 || criticalAlerts > 0) status = 'critical'
    else if (score < 70 || warningAlerts > 2) status = 'warning'
    else if (score < 85 || warningAlerts > 0) status = 'attention'

    // Gerar issues
    const issues: PoolHealthIssue[] = []

    if (criticalChips > 0) {
      issues.push({
        id: 'critical-trust',
        type: 'trust_dropping',
        severity: 'critical',
        message: `${criticalChips} chip(s) com trust crítico (< 30)`,
        affectedChips: criticalChips,
        recommendation: 'Pausar chips críticos e investigar causa',
      })
    }

    if (warningChips > 2) {
      issues.push({
        id: 'warning-trust',
        type: 'trust_dropping',
        severity: 'warning',
        message: `${warningChips} chip(s) com trust baixo (< 60)`,
        affectedChips: warningChips,
        recommendation: 'Monitorar de perto e reduzir volume de mensagens',
      })
    }

    // Agrupar alertas por tipo
    const alertsByType = alerts.reduce(
      (acc, a) => {
        acc[a.tipo] = (acc[a.tipo] || 0) + 1
        return acc
      },
      {} as Record<string, number>
    )

    Object.entries(alertsByType).forEach(([tipo, count]) => {
      if (count > 0) {
        issues.push({
          id: `alert-${tipo}`,
          type: tipo === 'TAXA_BLOCK_ALTA' ? 'ban_risk' : 'high_errors',
          severity: alerts.some((a) => a.tipo === tipo && a.severity === 'critico')
            ? 'critical'
            : 'warning',
          message: `${count} alerta(s) de ${tipo.toLowerCase().replace(/_/g, ' ')}`,
          affectedChips: count,
        })
      }
    })

    const response: PoolHealthStatus = {
      status,
      score: Math.round(score),
      issues,
      lastUpdated: new Date().toISOString(),
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error fetching pool health:', error)
    return NextResponse.json(
      {
        status: 'healthy',
        score: 100,
        issues: [],
        lastUpdated: new Date().toISOString(),
      } satisfies PoolHealthStatus,
      { status: 200 }
    )
  }
}
