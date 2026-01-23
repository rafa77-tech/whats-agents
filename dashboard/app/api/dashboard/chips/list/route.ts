/**
 * API: GET /api/dashboard/chips/list
 *
 * Retorna lista paginada de chips com detalhes.
 *
 * Query params:
 * - limit: numero maximo de chips (default: 10)
 * - offset: paginacao (default: 0)
 * - status: filtrar por status (opcional)
 * - sortBy: "trust" | "errors" | "messages" (default: "trust")
 * - order: "asc" | "desc" (default: "asc" para trust)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipStatus, TrustLevel } from '@/types/dashboard'

export const dynamic = 'force-dynamic'

interface ChipRow {
  id: string
  instance_name: string | null
  telefone: string
  status: ChipStatus
  trust_score: number | null
  trust_level: TrustLevel | null
  msgs_enviadas_hoje: number | null
  taxa_resposta: number | null
  erros_ultimas_24h: number | null
  fase_warmup: string | null
  warming_day: number | null
}

interface AlertRow {
  chip_id: string
  message: string
}

function getTrustLevel(score: number): TrustLevel {
  if (score >= 75) return 'verde'
  if (score >= 50) return 'amarelo'
  if (score >= 35) return 'laranja'
  return 'vermelho'
}

function getDailyLimit(status: ChipStatus, faseWarmup?: string | null): number {
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

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const searchParams = request.nextUrl.searchParams

    const limit = parseInt(searchParams.get('limit') || '10')
    const offset = parseInt(searchParams.get('offset') || '0')
    const status = searchParams.get('status')
    const sortBy = searchParams.get('sortBy') || 'trust'
    const order = searchParams.get('order') || 'asc'

    // Query base
    let query = supabase.from('chips').select(
      `
        id,
        instance_name,
        telefone,
        status,
        trust_score,
        trust_level,
        msgs_enviadas_hoje,
        taxa_resposta,
        erros_ultimas_24h,
        fase_warmup,
        warming_day
      `,
      { count: 'exact' }
    )

    // Filtro por status
    if (status) {
      query = query.eq('status', status)
    }

    // Ordenacao
    const sortColumn =
      sortBy === 'trust'
        ? 'trust_score'
        : sortBy === 'errors'
          ? 'erros_ultimas_24h'
          : 'msgs_enviadas_hoje'
    query = query.order(sortColumn, { ascending: order === 'asc' })

    // Paginacao
    query = query.range(offset, offset + limit - 1)

    const { data: chips, count, error } = await query

    if (error) throw error

    const typedChips = (chips as ChipRow[] | null) || []

    // Buscar alertas ativos
    const chipIds = typedChips.map((c) => c.id)
    let alertsMap = new Map<string, string>()

    if (chipIds.length > 0) {
      const { data: alerts } = await supabase
        .from('chip_alerts')
        .select('chip_id, message')
        .in('chip_id', chipIds)
        .eq('resolved', false)

      if (alerts) {
        alertsMap = new Map((alerts as AlertRow[]).map((a) => [a.chip_id, a.message]))
      }
    }

    // Formatar resposta
    const formattedChips = typedChips.map((chip) => ({
      id: chip.id,
      name: chip.instance_name || `Chip-${chip.id.slice(0, 4)}`,
      telefone: chip.telefone,
      status: chip.status,
      trustScore: chip.trust_score || 0,
      trustLevel: (chip.trust_level as TrustLevel) || getTrustLevel(chip.trust_score || 0),
      messagesToday: chip.msgs_enviadas_hoje || 0,
      dailyLimit: getDailyLimit(chip.status, chip.fase_warmup),
      responseRate: Number(((chip.taxa_resposta || 0) * 100).toFixed(1)),
      errorsLast24h: chip.erros_ultimas_24h || 0,
      hasActiveAlert: alertsMap.has(chip.id),
      alertMessage: alertsMap.get(chip.id),
      warmingDay: chip.warming_day,
    }))

    return NextResponse.json({
      chips: formattedChips,
      total: count || 0,
      limit,
      offset,
    })
  } catch (error) {
    console.error('Error fetching chip list:', error)
    return NextResponse.json({ error: 'Failed to fetch chip list' }, { status: 500 })
  }
}
