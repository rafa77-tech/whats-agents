/**
 * API: GET /api/dashboard/chips
 *
 * Retorna status do pool de chips no formato PoolStatus.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipStatus, TrustLevel } from '@/types/dashboard'
import { shouldUseMock, mockPoolStatus } from '@/lib/mock'
import type { PoolStatus, TrustLevelExtended } from '@/types/chips'

export const dynamic = 'force-dynamic'

interface ChipRow {
  id: string
  status: ChipStatus
  trust_score: number | null
  trust_level: TrustLevel | null
  msgs_enviadas_hoje: number | null
  limite_dia: number | null
  fase_warmup: string | null
}

interface AlertRow {
  id: string
  severity: string
}

function getTrustLevelExtended(score: number): TrustLevelExtended {
  if (score >= 80) return 'verde'
  if (score >= 60) return 'amarelo'
  if (score >= 40) return 'laranja'
  if (score >= 20) return 'vermelho'
  return 'critico'
}

function getDailyLimit(
  status: ChipStatus,
  faseWarmup?: string | null,
  limiteDia?: number | null
): number {
  if (limiteDia) return limiteDia
  if (status === 'active') return 100
  if (status === 'warming') {
    switch (faseWarmup) {
      case 'primeiros_contatos':
        return 10
      case 'expansao':
        return 30
      case 'pre_operacao':
        return 50
      default:
        return 30
    }
  }
  if (status === 'degraded') return 30
  return 0
}

export async function GET() {
  // Return mock data for E2E tests
  if (shouldUseMock()) {
    return NextResponse.json(mockPoolStatus)
  }

  try {
    const supabase = await createClient()

    // Buscar todos os chips
    const { data: chips, error } = await supabase.from('chips').select(`
        id,
        status,
        trust_score,
        trust_level,
        msgs_enviadas_hoje,
        limite_dia,
        fase_warmup
      `)

    if (error) throw error

    const typedChips = (chips as ChipRow[] | null) || []

    // Contagem por status
    const byStatus: Record<ChipStatus, number> = {
      active: 0,
      ready: 0,
      warming: 0,
      degraded: 0,
      paused: 0,
      banned: 0,
      pending: 0,
      provisioned: 0,
      cancelled: 0,
      offline: 0,
    }

    typedChips.forEach((chip) => {
      if (chip.status && chip.status in byStatus) {
        byStatus[chip.status as ChipStatus]++
      }
    })

    // Distribuição por trust level extendido
    const byTrustLevel: Record<TrustLevelExtended, number> = {
      verde: 0,
      amarelo: 0,
      laranja: 0,
      vermelho: 0,
      critico: 0,
    }

    let totalTrustScore = 0
    typedChips.forEach((chip) => {
      const score = chip.trust_score || 0
      totalTrustScore += score
      const level = getTrustLevelExtended(score)
      byTrustLevel[level]++
    })

    const totalChips = typedChips.length
    const avgTrustScore = totalChips > 0 ? totalTrustScore / totalChips : 0

    // Mensagens hoje e capacidade
    let totalMessagesToday = 0
    let totalDailyCapacity = 0

    typedChips.forEach((chip) => {
      totalMessagesToday += chip.msgs_enviadas_hoje || 0
      // Só contar capacidade de chips que podem enviar
      if (['active', 'warming', 'ready', 'degraded'].includes(chip.status)) {
        totalDailyCapacity += getDailyLimit(chip.status, chip.fase_warmup, chip.limite_dia)
      }
    })

    // Buscar alertas ativos
    const { data: alerts, error: alertsError } = await supabase
      .from('chip_alerts')
      .select('id, severity')
      .eq('resolved', false)

    let activeAlerts = 0
    let criticalAlerts = 0

    if (!alertsError && alerts) {
      const typedAlerts = alerts as AlertRow[]
      activeAlerts = typedAlerts.length
      criticalAlerts = typedAlerts.filter((a) => a.severity === 'critico').length
    }

    const poolStatus: PoolStatus = {
      total: totalChips,
      byStatus,
      byTrustLevel,
      avgTrustScore: Number(avgTrustScore.toFixed(1)),
      totalMessagesToday,
      totalDailyCapacity,
      activeAlerts,
      criticalAlerts,
    }

    return NextResponse.json(poolStatus)
  } catch (error) {
    console.error('Error fetching chip pool:', error)
    return NextResponse.json({ error: 'Failed to fetch chip pool data' }, { status: 500 })
  }
}
