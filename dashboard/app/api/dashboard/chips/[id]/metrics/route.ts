/**
 * API: GET /api/dashboard/chips/[id]/metrics
 *
 * Retorna metricas de um chip para um periodo especifico.
 * Sprint 39 - Chip Metrics
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipMetrics } from '@/types/chips'

export const dynamic = 'force-dynamic'

type Period = '1h' | '6h' | '24h' | '7d' | '30d'

function getPeriodInterval(period: Period): { current: Date; previous: Date } {
  const now = new Date()
  let currentStart: Date
  let previousStart: Date

  switch (period) {
    case '1h':
      currentStart = new Date(now.getTime() - 60 * 60 * 1000)
      previousStart = new Date(now.getTime() - 2 * 60 * 60 * 1000)
      break
    case '6h':
      currentStart = new Date(now.getTime() - 6 * 60 * 60 * 1000)
      previousStart = new Date(now.getTime() - 12 * 60 * 60 * 1000)
      break
    case '24h':
      currentStart = new Date(now.getTime() - 24 * 60 * 60 * 1000)
      previousStart = new Date(now.getTime() - 48 * 60 * 60 * 1000)
      break
    case '7d':
      currentStart = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      previousStart = new Date(now.getTime() - 14 * 24 * 60 * 60 * 1000)
      break
    case '30d':
      currentStart = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000)
      previousStart = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000)
      break
  }

  return { current: currentStart, previous: previousStart }
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id: chipId } = await params
    const searchParams = request.nextUrl.searchParams
    const period = (searchParams.get('period') || '24h') as Period

    // Verificar se chip existe
    const { data: chip, error: chipError } = await supabase
      .from('chips')
      .select('id, taxa_resposta, taxa_delivery')
      .eq('id', chipId)
      .single()

    if (chipError || !chip) {
      console.error('Metrics route - chip lookup failed:', { chipId, chipError })
      return NextResponse.json({ error: 'Chip not found' }, { status: 404 })
    }

    const { current: currentStart, previous: previousStart } = getPeriodInterval(period)
    const now = new Date()

    // Buscar interacoes do periodo atual
    const { data: currentInteractions } = await supabase
      .from('chip_interactions')
      .select('tipo, created_at')
      .eq('chip_id', chipId)
      .gte('created_at', currentStart.toISOString())
      .lte('created_at', now.toISOString())

    // Buscar interacoes do periodo anterior
    const { data: previousInteractions } = await supabase
      .from('chip_interactions')
      .select('tipo, created_at')
      .eq('chip_id', chipId)
      .gte('created_at', previousStart.toISOString())
      .lt('created_at', currentStart.toISOString())

    // Calcular metricas do periodo atual
    const currentRows = currentInteractions || []
    const messagesSent = currentRows.filter(
      (i) => i.tipo === 'msg_enviada' || i.tipo === 'warmup_msg'
    ).length
    const messagesReceived = currentRows.filter((i) => i.tipo === 'msg_recebida').length
    const errorCount = currentRows.filter((i) => i.tipo === 'erro').length

    // Calcular metricas do periodo anterior
    const previousRows = previousInteractions || []
    const previousMessagesSent = previousRows.filter(
      (i) => i.tipo === 'msg_enviada' || i.tipo === 'warmup_msg'
    ).length
    const previousErrorCount = previousRows.filter((i) => i.tipo === 'erro').length
    const previousReceived = previousRows.filter((i) => i.tipo === 'msg_recebida').length

    // Calcular taxas
    const responseRate =
      messagesSent > 0 ? Number(((messagesReceived / messagesSent) * 100).toFixed(1)) : 0
    const previousResponseRate =
      previousMessagesSent > 0
        ? Number(((previousReceived / previousMessagesSent) * 100).toFixed(1))
        : 0

    // Usar taxa de entrega do chip ou padrao
    const deliveryRate = Number(((chip.taxa_delivery ?? 0.95) * 100).toFixed(1))

    // Tempo medio de resposta (mock - precisaria de dados mais detalhados)
    const avgResponseTime = messagesReceived > 0 ? 45 + Math.random() * 30 : 0

    const metrics: ChipMetrics = {
      period,
      messagesSent,
      messagesReceived,
      responseRate,
      deliveryRate,
      errorCount,
      avgResponseTime: Number(avgResponseTime.toFixed(1)),
      previousMessagesSent,
      previousResponseRate,
      previousErrorCount,
    }

    return NextResponse.json(metrics)
  } catch (error) {
    console.error('Error fetching chip metrics:', error)
    return NextResponse.json({ error: 'Failed to fetch chip metrics' }, { status: 500 })
  }
}
