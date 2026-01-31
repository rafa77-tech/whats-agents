/**
 * API: GET /api/dashboard/metrics
 *
 * Retorna metricas vs meta (taxa resposta, conversao, fechamentos).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getPeriodDates, calculateRate, validatePeriod } from '@/lib/dashboard/calculations'

export const dynamic = 'force-dynamic'

// Metas definidas no CLAUDE.md
const METAS = {
  responseRate: 30,
  conversionRate: 25,
  closingsPerWeek: 15,
}

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const period = validatePeriod(request.nextUrl.searchParams.get('period'))
    const { currentStart, currentEnd, previousStart, previousEnd, days } = getPeriodDates(period)

    // Medicos unicos contatados (current) - clientes com interacao de saida
    const { data: contatadosCurrent } = await supabase
      .from('interacoes')
      .select('cliente_id')
      .eq('tipo', 'saida')
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)
    const setContatadosCurrent = new Set(contatadosCurrent?.map((i) => i.cliente_id) || [])

    // Medicos unicos que responderam (current) - clientes com interacao de entrada
    const { data: responderamCurrent } = await supabase
      .from('interacoes')
      .select('cliente_id')
      .eq('tipo', 'entrada')
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)
    const setResponderamCurrent = new Set(responderamCurrent?.map((i) => i.cliente_id) || [])

    // Intersecao: medicos contatados que responderam (current)
    const medicosContatadosCurrent = setContatadosCurrent.size
    const medicosResponderamCurrent = Array.from(setResponderamCurrent).filter((id) =>
      setContatadosCurrent.has(id)
    ).length

    // Medicos unicos contatados (previous)
    const { data: contatadosPrevious } = await supabase
      .from('interacoes')
      .select('cliente_id')
      .eq('tipo', 'saida')
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)
    const setContatadosPrevious = new Set(contatadosPrevious?.map((i) => i.cliente_id) || [])

    // Medicos unicos que responderam (previous)
    const { data: responderamPrevious } = await supabase
      .from('interacoes')
      .select('cliente_id')
      .eq('tipo', 'entrada')
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)
    const setResponderamPrevious = new Set(responderamPrevious?.map((i) => i.cliente_id) || [])

    // Intersecao: medicos contatados que responderam (previous)
    const medicosContatadosPrevious = setContatadosPrevious.size
    const medicosResponderamPrevious = Array.from(setResponderamPrevious).filter((id) =>
      setContatadosPrevious.has(id)
    ).length

    // Fechamentos (current) - conversations com status fechado/completed
    const { count: fechamentosCurrent } = await supabase
      .from('conversations')
      .select('*', { count: 'exact', head: true })
      .in('status', ['fechado', 'completed', 'convertido'])
      .gte('completed_at', currentStart)
      .lte('completed_at', currentEnd)

    // Fechamentos (previous)
    const { count: fechamentosPrevious } = await supabase
      .from('conversations')
      .select('*', { count: 'exact', head: true })
      .in('status', ['fechado', 'completed', 'convertido'])
      .gte('completed_at', previousStart)
      .lte('completed_at', previousEnd)

    // Calculos
    const responseRateCurrent = calculateRate(medicosResponderamCurrent, medicosContatadosCurrent)
    const responseRatePrevious = calculateRate(
      medicosResponderamPrevious,
      medicosContatadosPrevious
    )

    // Conversao: fechamentos / medicos que responderam
    const conversionCurrent = calculateRate(fechamentosCurrent || 0, medicosResponderamCurrent)
    const conversionPrevious = calculateRate(fechamentosPrevious || 0, medicosResponderamPrevious)

    // Normalizar fechamentos por semana
    const weeksInPeriod = days / 7
    const closingsPerWeekCurrent = Number(((fechamentosCurrent || 0) / weeksInPeriod).toFixed(1))
    const closingsPerWeekPrevious = Number(((fechamentosPrevious || 0) / weeksInPeriod).toFixed(1))

    return NextResponse.json({
      metrics: {
        responseRate: {
          value: responseRateCurrent,
          previous: responseRatePrevious,
          meta: METAS.responseRate,
        },
        conversionRate: {
          value: conversionCurrent,
          previous: conversionPrevious,
          meta: METAS.conversionRate,
        },
        closingsPerWeek: {
          value: closingsPerWeekCurrent,
          previous: closingsPerWeekPrevious,
          meta: METAS.closingsPerWeek,
        },
      },
      period: {
        start: currentStart,
        end: currentEnd,
        days,
      },
    })
  } catch (error) {
    console.error('Error fetching dashboard metrics:', error)
    return NextResponse.json({ error: 'Failed to fetch metrics' }, { status: 500 })
  }
}
