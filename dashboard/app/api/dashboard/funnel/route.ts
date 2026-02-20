/**
 * API: GET /api/dashboard/funnel
 *
 * Retorna dados do funil de conversao.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { getPeriodDates, validatePeriod } from '@/lib/dashboard/calculations'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const period = validatePeriod(request.nextUrl.searchParams.get('period'))
    const { currentStart, currentEnd, previousStart, previousEnd, days } = getPeriodDates(period)

    // === FUNIL POR CONVERSAS ÚNICAS ===
    // Contamos conversas únicas em cada etapa, não mensagens individuais

    // === Enviadas (conversas únicas onde Julia enviou mensagem) ===
    const { data: conversasEnviadasCurrent } = await supabase
      .from('interacoes')
      .select('conversation_id')
      .eq('tipo', 'saida')
      .not('conversation_id', 'is', null)
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const enviadasSetCurrent = new Set(
      (conversasEnviadasCurrent || []).map((r) => r.conversation_id)
    )
    const enviadasCurrent = enviadasSetCurrent.size

    const { data: conversasEnviadasPrevious } = await supabase
      .from('interacoes')
      .select('conversation_id')
      .eq('tipo', 'saida')
      .not('conversation_id', 'is', null)
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)

    const enviadasSetPrevious = new Set(
      (conversasEnviadasPrevious || []).map((r) => r.conversation_id)
    )
    const enviadasPrevious = enviadasSetPrevious.size

    // === Entregues (conversas onde pelo menos uma msg foi entregue) ===
    // Por enquanto, assumimos que todas enviadas foram entregues (até termos delivery_status populado)
    const { data: conversasEntreguesCurrent } = await supabase
      .from('interacoes')
      .select('conversation_id')
      .eq('tipo', 'saida')
      .not('conversation_id', 'is', null)
      .or('delivery_status.is.null,delivery_status.in.(sent,delivered,read)')
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const entreguesSetCurrent = new Set(
      (conversasEntreguesCurrent || []).map((r) => r.conversation_id)
    )
    const entreguesCurrent = entreguesSetCurrent.size

    const { data: conversasEntreguesPrevious } = await supabase
      .from('interacoes')
      .select('conversation_id')
      .eq('tipo', 'saida')
      .not('conversation_id', 'is', null)
      .or('delivery_status.is.null,delivery_status.in.(sent,delivered,read)')
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)

    const entreguesSetPrevious = new Set(
      (conversasEntreguesPrevious || []).map((r) => r.conversation_id)
    )
    const entreguesPrevious = entreguesSetPrevious.size

    // === Respostas (conversas únicas que receberam resposta) ===
    const { data: conversasRespostaCurrent } = await supabase
      .from('interacoes')
      .select('conversation_id')
      .eq('tipo', 'entrada')
      .not('conversation_id', 'is', null)
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    // Filtrar apenas conversas onde Julia enviou mensagem
    const respostasSetCurrent = new Set(
      (conversasRespostaCurrent || [])
        .map((r) => r.conversation_id)
        .filter((id) => enviadasSetCurrent.has(id))
    )
    const respostasCurrent = respostasSetCurrent.size

    const { data: conversasRespostaPrevious } = await supabase
      .from('interacoes')
      .select('conversation_id')
      .eq('tipo', 'entrada')
      .not('conversation_id', 'is', null)
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)

    const respostasSetPrevious = new Set(
      (conversasRespostaPrevious || [])
        .map((r) => r.conversation_id)
        .filter((id) => enviadasSetPrevious.has(id))
    )
    const respostasPrevious = respostasSetPrevious.size

    // === Interesse (conversations com stage que indica interesse) ===

    const { count: interesseCurrent } = await supabase
      .from('conversations')
      .select('*', { count: 'exact', head: true })
      .in('stage', ['interesse', 'negociacao', 'qualificado', 'proposta'])
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const { count: interessePrevious } = await supabase
      .from('conversations')
      .select('*', { count: 'exact', head: true })
      .in('stage', ['interesse', 'negociacao', 'qualificado', 'proposta'])
      .gte('created_at', previousStart)
      .lte('created_at', previousEnd)

    // === Fechadas (conversations com status fechado/completed) ===

    const { count: fechadasCurrent } = await supabase
      .from('conversations')
      .select('*', { count: 'exact', head: true })
      .in('status', ['fechado', 'completed', 'convertido'])
      .gte('completed_at', currentStart)
      .lte('completed_at', currentEnd)

    const { count: fechadasPrevious } = await supabase
      .from('conversations')
      .select('*', { count: 'exact', head: true })
      .in('status', ['fechado', 'completed', 'convertido'])
      .gte('completed_at', previousStart)
      .lte('completed_at', previousEnd)

    // Calculate percentages based on enviadas
    const enviadasCount = enviadasCurrent || 0
    const entreguesCount = entreguesCurrent || 0
    const respostasCount = respostasCurrent || 0
    const interesseCount = interesseCurrent || 0
    const fechadasCount = fechadasCurrent || 0

    const safePercent = (n: number, d: number) => (d > 0 ? Number(((n / d) * 100).toFixed(1)) : 0)

    return NextResponse.json({
      stages: [
        {
          id: 'enviadas',
          label: 'Enviadas',
          count: enviadasCount,
          previousCount: enviadasPrevious || 0,
          percentage: enviadasCount > 0 ? 100 : 0,
        },
        {
          id: 'entregues',
          label: 'Entregues',
          count: entreguesCount,
          previousCount: entreguesPrevious || 0,
          percentage: safePercent(entreguesCount, enviadasCount),
        },
        {
          id: 'respostas',
          label: 'Respostas',
          count: respostasCount,
          previousCount: respostasPrevious || 0,
          percentage: safePercent(respostasCount, enviadasCount),
        },
        {
          id: 'interesse',
          label: 'Interesse',
          count: interesseCount,
          previousCount: interessePrevious || 0,
          percentage: safePercent(interesseCount, enviadasCount),
        },
        {
          id: 'fechadas',
          label: 'Fechadas',
          count: fechadasCount,
          previousCount: fechadasPrevious || 0,
          percentage: safePercent(fechadasCount, enviadasCount),
        },
      ],
      period: `${days} dias`,
    })
  } catch (error) {
    console.error('Error fetching funnel data:', error)
    return NextResponse.json({ error: 'Failed to fetch funnel data' }, { status: 500 })
  }
}
