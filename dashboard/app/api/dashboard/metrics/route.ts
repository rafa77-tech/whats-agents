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

    // Mensagens enviadas (current) - interacoes de saida (Julia enviou)
    const { count: enviadasCurrent } = await supabase
      .from('interacoes')
      .select('*', { count: 'exact', head: true })
      .eq('tipo', 'saida')
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    // Respostas recebidas (current) - interacoes de entrada (medico respondeu)
    const { count: respostasCurrent } = await supabase
      .from('interacoes')
      .select('*', { count: 'exact', head: true })
      .eq('tipo', 'entrada')
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    // Mensagens enviadas (previous)
    const { count: enviadasPrevious } = await supabase
      .from('interacoes')
      .select('*', { count: 'exact', head: true })
      .eq('tipo', 'saida')
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)

    // Respostas recebidas (previous)
    const { count: respostasPrevious } = await supabase
      .from('interacoes')
      .select('*', { count: 'exact', head: true })
      .eq('tipo', 'entrada')
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)

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
    const responseRateCurrent = calculateRate(respostasCurrent || 0, enviadasCurrent || 0)
    const responseRatePrevious = calculateRate(respostasPrevious || 0, enviadasPrevious || 0)

    // Conversao: fechamentos / respostas
    const conversionCurrent = calculateRate(fechamentosCurrent || 0, respostasCurrent || 0)
    const conversionPrevious = calculateRate(fechamentosPrevious || 0, respostasPrevious || 0)

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
