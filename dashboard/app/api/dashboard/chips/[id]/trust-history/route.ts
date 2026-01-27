/**
 * API: GET /api/dashboard/chips/[id]/trust-history
 *
 * Retorna historico de trust score de um chip.
 * Sprint 39 - Chip Trust History
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type {
  ChipTrustHistory,
  TrustHistoryPoint,
  TrustEvent,
  TrustLevelExtended,
} from '@/types/chips'

export const dynamic = 'force-dynamic'

interface TransitionRow {
  id: string
  from_trust_score: number
  to_trust_score: number
  from_status: string
  to_status: string
  triggered_by: string
  created_at: string
}

function getTrustLevel(score: number): TrustLevelExtended {
  if (score >= 80) return 'verde'
  if (score >= 60) return 'amarelo'
  if (score >= 40) return 'laranja'
  if (score >= 20) return 'vermelho'
  return 'critico'
}

function getEventType(
  fromScore: number,
  toScore: number,
  fromStatus: string,
  toStatus: string
): 'increase' | 'decrease' | 'phase_change' | 'alert' {
  if (fromStatus !== toStatus) return 'phase_change'
  if (toScore < fromScore && toScore < 40) return 'alert'
  if (toScore > fromScore) return 'increase'
  return 'decrease'
}

function getEventDescription(
  fromScore: number,
  toScore: number,
  fromStatus: string,
  toStatus: string,
  triggeredBy: string
): string {
  if (fromStatus !== toStatus) {
    return `Status alterado de ${fromStatus} para ${toStatus}`
  }
  const diff = toScore - fromScore
  const direction = diff > 0 ? 'aumentou' : 'diminuiu'
  const reason = triggeredBy || 'ajuste automatico'
  return `Trust score ${direction} ${Math.abs(diff)} pontos (${reason})`
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id: chipId } = await params
    const searchParams = request.nextUrl.searchParams
    const days = parseInt(searchParams.get('days') || '30', 10)

    // Verificar se chip existe
    const { data: chip, error: chipError } = await supabase
      .from('chips')
      .select('id, trust_score, created_at')
      .eq('id', chipId)
      .single()

    if (chipError || !chip) {
      return NextResponse.json({ error: 'Chip not found' }, { status: 404 })
    }

    const startDate = new Date()
    startDate.setDate(startDate.getDate() - days)

    // Buscar transicoes do periodo
    const { data: transitions } = await supabase
      .from('chip_transitions')
      .select(
        'id, from_trust_score, to_trust_score, from_status, to_status, triggered_by, created_at'
      )
      .eq('chip_id', chipId)
      .gte('created_at', startDate.toISOString())
      .order('created_at', { ascending: true })

    const transitionRows = (transitions as TransitionRow[] | null) || []

    // Construir historico de pontos
    const history: TrustHistoryPoint[] = []
    const events: TrustEvent[] = []

    // Adicionar ponto inicial (trust score no inicio do periodo ou quando chip foi criado)
    const chipCreatedAt = new Date(chip.created_at)
    const initialTimestamp = chipCreatedAt > startDate ? chipCreatedAt : startDate
    const firstTransition = transitionRows[0]
    const initialScore = firstTransition
      ? firstTransition.from_trust_score
      : (chip.trust_score ?? 50)

    history.push({
      timestamp: initialTimestamp.toISOString(),
      score: initialScore,
      level: getTrustLevel(initialScore),
    })

    // Processar transicoes
    for (const t of transitionRows) {
      // Adicionar ponto ao historico
      history.push({
        timestamp: t.created_at,
        score: t.to_trust_score,
        level: getTrustLevel(t.to_trust_score),
      })

      // Adicionar evento
      events.push({
        id: t.id,
        timestamp: t.created_at,
        type: getEventType(t.from_trust_score, t.to_trust_score, t.from_status, t.to_status),
        description: getEventDescription(
          t.from_trust_score,
          t.to_trust_score,
          t.from_status,
          t.to_status,
          t.triggered_by
        ),
        scoreBefore: t.from_trust_score,
        scoreAfter: t.to_trust_score,
      })
    }

    // Adicionar ponto atual se houver diferenca
    const currentScore = chip.trust_score ?? 50
    const lastHistoryPoint = history[history.length - 1]
    const lastHistoryScore = lastHistoryPoint?.score ?? 0
    if (currentScore !== lastHistoryScore) {
      history.push({
        timestamp: new Date().toISOString(),
        score: currentScore,
        level: getTrustLevel(currentScore),
      })
    }

    const response: ChipTrustHistory = {
      history,
      events: events.reverse(), // Mais recentes primeiro
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error fetching chip trust history:', error)
    return NextResponse.json({ error: 'Failed to fetch chip trust history' }, { status: 500 })
  }
}
