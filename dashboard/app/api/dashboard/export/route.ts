/**
 * API: GET /api/dashboard/export
 *
 * Exports dashboard data in CSV or PDF format.
 *
 * Query params:
 * - format: "csv" (default) | "pdf"
 * - period: "7d", "14d", "30d" (default: "7d")
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { generateDashboardCSV } from '@/lib/dashboard/csv-generator'
import { generateDashboardPDF } from '@/lib/dashboard/pdf-generator'
import { getPeriodDates } from '@/lib/dashboard/calculations'
import { type DashboardExportData } from '@/types/dashboard'

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams
  const format = searchParams.get('format') || 'csv'
  const period = searchParams.get('period') || '7d'

  try {
    const supabase = await createClient()

    if (format !== 'csv' && format !== 'pdf') {
      return NextResponse.json(
        { error: 'Format not supported. Use format=csv or format=pdf' },
        { status: 400 }
      )
    }

    const { currentStart, currentEnd } = getPeriodDates(period)

    // Collect all dashboard data
    const exportData: DashboardExportData = {
      period: { start: currentStart, end: currentEnd },
      metrics: [],
      quality: [],
      chips: [],
      funnel: [],
    }

    // Fetch metrics from conversations
    const { count: totalConversas } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const { count: respostas } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)
      .in('stage', ['respondido', 'interesse', 'negociacao', 'qualificado'])

    const { count: fechamentos } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)
      .in('status', ['fechado', 'completed'])

    const taxaResposta =
      totalConversas && totalConversas > 0 && respostas ? (respostas / totalConversas) * 100 : 0
    const taxaConversao =
      respostas && respostas > 0 && fechamentos ? (fechamentos / respostas) * 100 : 0

    // Calculate previous period for comparison
    const periodDays = period === '7d' ? 7 : period === '14d' ? 14 : 30
    const previousStart = new Date(
      new Date(currentStart).getTime() - periodDays * 24 * 60 * 60 * 1000
    ).toISOString()
    const previousEnd = currentStart

    // Fetch previous period metrics
    const { count: prevConversas } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)

    const { count: prevRespostas } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)
      .in('stage', ['respondido', 'interesse', 'negociacao', 'qualificado'])

    const { count: prevFechamentos } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)
      .in('status', ['fechado', 'completed'])

    const prevTaxaResposta =
      prevConversas && prevConversas > 0 && prevRespostas
        ? (prevRespostas / prevConversas) * 100
        : 0
    const prevTaxaConversao =
      prevRespostas && prevRespostas > 0 && prevFechamentos
        ? (prevFechamentos / prevRespostas) * 100
        : 0

    exportData.metrics = [
      {
        name: 'Taxa de Resposta',
        current: Number(taxaResposta.toFixed(1)),
        previous: Number(prevTaxaResposta.toFixed(1)),
        meta: 30,
        unit: 'percent',
      },
      {
        name: 'Taxa de Conversao',
        current: Number(taxaConversao.toFixed(1)),
        previous: Number(prevTaxaConversao.toFixed(1)),
        meta: 25,
        unit: 'percent',
      },
      {
        name: 'Fechamentos/Semana',
        current: fechamentos ?? 0,
        previous: prevFechamentos ?? 0,
        meta: 15,
        unit: 'number',
      },
    ]

    // Fetch real quality metrics
    const { count: botDetections } = await supabase
      .from('metricas_deteccao_bot')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const { count: prevBotDetections } = await supabase
      .from('metricas_deteccao_bot')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)

    const botRate =
      totalConversas && totalConversas > 0 ? ((botDetections ?? 0) / totalConversas) * 100 : 0
    const prevBotRate =
      prevConversas && prevConversas > 0 ? ((prevBotDetections ?? 0) / prevConversas) * 100 : 0

    const { data: latencyData } = await supabase
      .from('metricas_conversa')
      .select('tempo_medio_resposta_segundos')
      .not('tempo_medio_resposta_segundos', 'is', null)
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const { data: prevLatencyData } = await supabase
      .from('metricas_conversa')
      .select('tempo_medio_resposta_segundos')
      .not('tempo_medio_resposta_segundos', 'is', null)
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)

    const avgLatency =
      latencyData && latencyData.length > 0
        ? latencyData.reduce((sum, r) => sum + (Number(r.tempo_medio_resposta_segundos) || 0), 0) /
          latencyData.length
        : 0
    const prevAvgLatency =
      prevLatencyData && prevLatencyData.length > 0
        ? prevLatencyData.reduce(
            (sum, r) => sum + (Number(r.tempo_medio_resposta_segundos) || 0),
            0
          ) / prevLatencyData.length
        : 0

    const { count: handoffs } = await supabase
      .from('handoffs')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const { count: prevHandoffs } = await supabase
      .from('handoffs')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)

    const handoffRate =
      totalConversas && totalConversas > 0 ? ((handoffs ?? 0) / totalConversas) * 100 : 0
    const prevHandoffRate =
      prevConversas && prevConversas > 0 ? ((prevHandoffs ?? 0) / prevConversas) * 100 : 0

    exportData.quality = [
      {
        name: 'Deteccao Bot',
        current: Number(botRate.toFixed(2)),
        previous: Number(prevBotRate.toFixed(2)),
        meta: '<1%',
        unit: 'percent',
      },
      {
        name: 'Latencia Media',
        current: Number(avgLatency.toFixed(1)),
        previous: Number(prevAvgLatency.toFixed(1)),
        meta: '<30s',
        unit: 'seconds',
      },
      {
        name: 'Taxa Handoff',
        current: Number(handoffRate.toFixed(2)),
        previous: Number(prevHandoffRate.toFixed(2)),
        meta: '<5%',
        unit: 'percent',
      },
    ]

    // Fetch chips data
    const { data: chips } = await supabase
      .from('chips')
      .select(
        'instance_name, status, trust_score, msgs_enviadas_hoje, taxa_resposta, erros_ultimas_24h'
      )
      .in('status', ['active', 'ready', 'warming', 'degraded'])
      .order('instance_name')

    interface ChipRow {
      instance_name: string | null
      status: string
      trust_score: number | null
      msgs_enviadas_hoje: number | null
      taxa_resposta: number | null
      erros_ultimas_24h: number | null
    }

    const typedChips = chips as unknown as ChipRow[] | null

    exportData.chips =
      typedChips?.map((c) => ({
        name: c.instance_name ?? 'Chip',
        status: c.status,
        trust: c.trust_score ?? 0,
        messagesToday: c.msgs_enviadas_hoje ?? 0,
        responseRate: (c.taxa_resposta ?? 0) * 100,
        errors: c.erros_ultimas_24h ?? 0,
      })) ?? []

    // Funnel data - current period
    const { count: enviadas } = await supabase
      .from('fila_mensagens')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)

    const { count: entregues } = await supabase
      .from('fila_mensagens')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)
      .eq('outcome', 'delivered')

    const { count: interesse } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', currentStart)
      .lte('created_at', currentEnd)
      .in('stage', ['interesse', 'negociacao', 'qualificado'])

    // Funnel data - previous period for change calculation
    const { count: prevEnviadas } = await supabase
      .from('fila_mensagens')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)

    const { count: prevEntregues } = await supabase
      .from('fila_mensagens')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)
      .eq('outcome', 'delivered')

    const { count: prevInteresse } = await supabase
      .from('conversations')
      .select('id', { count: 'exact', head: true })
      .gte('created_at', previousStart)
      .lt('created_at', previousEnd)
      .in('stage', ['interesse', 'negociacao', 'qualificado'])

    const enviadasCount = enviadas ?? 0
    const entreguesCount = entregues ?? 0
    const respostasCount = respostas ?? 0
    const interesseCount = interesse ?? 0
    const fechadasCount = fechamentos ?? 0

    const prevEnviadasCount = prevEnviadas ?? 0
    const prevEntreguesCount = prevEntregues ?? 0
    const prevRespostasCount = prevRespostas ?? 0
    const prevInteresseCount = prevInteresse ?? 0
    const prevFechadasCount = prevFechamentos ?? 0

    // Calculate percentage change
    const calcChange = (current: number, previous: number): number => {
      if (previous === 0) return current > 0 ? 100 : 0
      return Number((((current - previous) / previous) * 100).toFixed(1))
    }

    exportData.funnel = [
      {
        stage: 'Enviadas',
        count: enviadasCount,
        percentage: 100,
        change: calcChange(enviadasCount, prevEnviadasCount),
      },
      {
        stage: 'Entregues',
        count: entreguesCount,
        percentage: enviadasCount > 0 ? (entreguesCount / enviadasCount) * 100 : 0,
        change: calcChange(entreguesCount, prevEntreguesCount),
      },
      {
        stage: 'Respostas',
        count: respostasCount,
        percentage: enviadasCount > 0 ? (respostasCount / enviadasCount) * 100 : 0,
        change: calcChange(respostasCount, prevRespostasCount),
      },
      {
        stage: 'Interesse',
        count: interesseCount,
        percentage: enviadasCount > 0 ? (interesseCount / enviadasCount) * 100 : 0,
        change: calcChange(interesseCount, prevInteresseCount),
      },
      {
        stage: 'Fechadas',
        count: fechadasCount,
        percentage: enviadasCount > 0 ? (fechadasCount / enviadasCount) * 100 : 0,
        change: calcChange(fechadasCount, prevFechadasCount),
      },
    ]

    // Generate filename with date
    const dateStr = new Date().toISOString().split('T')[0] ?? 'export'

    // Generate and return based on format
    if (format === 'pdf') {
      const pdfBuffer = generateDashboardPDF(exportData)
      const filename = `dashboard-julia-${period}-${dateStr}.pdf`

      return new NextResponse(Buffer.from(pdfBuffer), {
        headers: {
          'Content-Type': 'application/pdf',
          'Content-Disposition': `attachment; filename="${filename}"`,
        },
      })
    }

    // Default: CSV
    const csv = generateDashboardCSV(exportData)
    const filename = `dashboard-julia-${period}-${dateStr}.csv`

    return new NextResponse(csv, {
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': `attachment; filename="${filename}"`,
      },
    })
  } catch (error) {
    console.error('Error exporting dashboard:', error)
    return NextResponse.json({ error: 'Failed to export dashboard' }, { status: 500 })
  }
}
