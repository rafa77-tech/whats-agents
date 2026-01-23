/**
 * API: GET /api/dashboard/chips/[id]
 *
 * Retorna detalhes de um chip especifico, incluindo alertas e transicoes recentes.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipStatus, TrustLevel } from '@/types/dashboard'

export const dynamic = 'force-dynamic'

interface ChipFullRow {
  id: string
  instance_name: string | null
  telefone: string
  status: ChipStatus
  trust_score: number | null
  trust_level: TrustLevel | null
  msgs_enviadas_hoje: number | null
  msgs_enviadas_total: number | null
  taxa_resposta: number | null
  taxa_block: number | null
  erros_ultimas_24h: number | null
  dias_sem_erro: number | null
  fase_warmup: string | null
  warming_day: number | null
  warming_started_at: string | null
  created_at: string
  promoted_to_active_at: string | null
  last_activity_start: string | null
  limite_dia: number | null
}

interface AlertRow {
  id: string
  severity: string
  message: string
  created_at: string
}

interface TransitionRow {
  from_status: string
  to_status: string
  from_trust_score: number
  to_trust_score: number
  triggered_by: string
  created_at: string
}

function getTrustLevel(score: number): TrustLevel {
  if (score >= 75) return 'verde'
  if (score >= 50) return 'amarelo'
  if (score >= 35) return 'laranja'
  return 'vermelho'
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

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id: chipId } = await params

    // Buscar chip
    const { data: chip, error: chipError } = await supabase
      .from('chips')
      .select('*')
      .eq('id', chipId)
      .single()

    if (chipError || !chip) {
      return NextResponse.json({ error: 'Chip not found' }, { status: 404 })
    }

    const typedChip = chip as ChipFullRow

    // Buscar alertas ativos
    const { data: alerts } = await supabase
      .from('chip_alerts')
      .select('id, severity, message, created_at')
      .eq('chip_id', chipId)
      .eq('resolved', false)
      .order('created_at', { ascending: false })
      .limit(5)

    // Buscar transicoes recentes
    const { data: transitions } = await supabase
      .from('chip_transitions')
      .select('from_status, to_status, from_trust_score, to_trust_score, triggered_by, created_at')
      .eq('chip_id', chipId)
      .order('created_at', { ascending: false })
      .limit(10)

    // Formatar resposta
    const trustLevel =
      (typedChip.trust_level as TrustLevel) || getTrustLevel(typedChip.trust_score || 0)

    return NextResponse.json({
      chip: {
        id: typedChip.id,
        name: typedChip.instance_name || `Chip-${typedChip.id.slice(0, 4)}`,
        telefone: typedChip.telefone,
        status: typedChip.status,
        trustScore: typedChip.trust_score || 0,
        trustLevel,
        messagesToday: typedChip.msgs_enviadas_hoje || 0,
        messagesTotal: typedChip.msgs_enviadas_total || 0,
        dailyLimit: getDailyLimit(typedChip.status, typedChip.fase_warmup, typedChip.limite_dia),
        responseRate: Number(((typedChip.taxa_resposta || 0) * 100).toFixed(1)),
        blockRate: Number(((typedChip.taxa_block || 0) * 100).toFixed(1)),
        errorsLast24h: typedChip.erros_ultimas_24h || 0,
        daysWithoutError: typedChip.dias_sem_erro || 0,
        warmingPhase: typedChip.fase_warmup,
        warmingDay: typedChip.warming_day,
        warmingStartedAt: typedChip.warming_started_at,
        createdAt: typedChip.created_at,
        promotedToActiveAt: typedChip.promoted_to_active_at,
        lastActivityAt: typedChip.last_activity_start,
      },
      alerts:
        (alerts as AlertRow[] | null)?.map((a) => ({
          id: a.id,
          severity: a.severity,
          message: a.message,
          createdAt: a.created_at,
        })) || [],
      recentTransitions:
        (transitions as TransitionRow[] | null)?.map((t) => ({
          fromStatus: t.from_status,
          toStatus: t.to_status,
          fromTrust: t.from_trust_score,
          toTrust: t.to_trust_score,
          triggeredBy: t.triggered_by,
          createdAt: t.created_at,
        })) || [],
    })
  } catch (error) {
    console.error('Error fetching chip detail:', error)
    return NextResponse.json({ error: 'Failed to fetch chip detail' }, { status: 500 })
  }
}
