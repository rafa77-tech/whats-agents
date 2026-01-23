/**
 * API: GET /api/dashboard/trends
 *
 * Returns sparkline data for key metrics over the selected period.
 * Data is aggregated by day from real database tables.
 *
 * Query params:
 * - period: "7d", "14d", or "30d" (default: "7d")
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import { validatePeriod } from '@/lib/dashboard/calculations'

export const dynamic = 'force-dynamic'

interface TrendDataPoint {
  date: string
  value: number
}

interface DailyMetrics {
  date: string
  enviadas: number
  respostas: number
  latencia_soma: number
  latencia_count: number
  bot_detections: number
  conversations: number
}

export async function GET(request: NextRequest) {
  try {
    const supabase = await createClient()
    const period = validatePeriod(request.nextUrl.searchParams.get('period'))
    const days = period === '7d' ? 7 : period === '14d' ? 14 : 30

    // Calculate date range
    const endDate = new Date()
    const startDate = new Date()
    startDate.setDate(startDate.getDate() - days)

    // Generate array of dates for the period
    const dates: string[] = []
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      dates.push(date.toISOString().split('T')[0] ?? '')
    }

    // Initialize metrics map
    const metricsMap = new Map<string, DailyMetrics>()
    dates.forEach((date) => {
      metricsMap.set(date, {
        date,
        enviadas: 0,
        respostas: 0,
        latencia_soma: 0,
        latencia_count: 0,
        bot_detections: 0,
        conversations: 0,
      })
    })

    // Fetch messages sent per day (fila_mensagens with outcome = delivered)
    const { data: msgData } = await supabase
      .from('fila_mensagens')
      .select('created_at')
      .eq('outcome', 'delivered')
      .gte('created_at', startDate.toISOString())
      .lte('created_at', endDate.toISOString())

    msgData?.forEach((row) => {
      const date = new Date(row.created_at).toISOString().split('T')[0] ?? ''
      const metrics = metricsMap.get(date)
      if (metrics) {
        metrics.enviadas++
      }
    })

    // Fetch responses per day (interacoes with direcao = in)
    const { data: respData } = await supabase
      .from('interacoes')
      .select('created_at')
      .eq('direcao', 'in')
      .gte('created_at', startDate.toISOString())
      .lte('created_at', endDate.toISOString())

    respData?.forEach((row) => {
      const date = new Date(row.created_at).toISOString().split('T')[0] ?? ''
      const metrics = metricsMap.get(date)
      if (metrics) {
        metrics.respostas++
      }
    })

    // Fetch latency data from metricas_conversa
    const { data: latencyData } = await supabase
      .from('metricas_conversa')
      .select('created_at, tempo_medio_resposta_segundos')
      .not('tempo_medio_resposta_segundos', 'is', null)
      .gte('created_at', startDate.toISOString())
      .lte('created_at', endDate.toISOString())

    latencyData?.forEach((row) => {
      const date = new Date(row.created_at).toISOString().split('T')[0] ?? ''
      const metrics = metricsMap.get(date)
      if (metrics && row.tempo_medio_resposta_segundos) {
        metrics.latencia_soma += Number(row.tempo_medio_resposta_segundos)
        metrics.latencia_count++
      }
    })

    // Fetch bot detections per day
    const { data: botData } = await supabase
      .from('metricas_deteccao_bot')
      .select('created_at')
      .gte('created_at', startDate.toISOString())
      .lte('created_at', endDate.toISOString())

    botData?.forEach((row) => {
      const date = new Date(row.created_at).toISOString().split('T')[0] ?? ''
      const metrics = metricsMap.get(date)
      if (metrics) {
        metrics.bot_detections++
      }
    })

    // Fetch conversations per day (for bot detection rate calculation)
    const { data: convData } = await supabase
      .from('conversations')
      .select('created_at')
      .gte('created_at', startDate.toISOString())
      .lte('created_at', endDate.toISOString())

    convData?.forEach((row) => {
      const date = new Date(row.created_at).toISOString().split('T')[0] ?? ''
      const metrics = metricsMap.get(date)
      if (metrics) {
        metrics.conversations++
      }
    })

    // Fetch current average trust score from chips
    const { data: chipsData } = await supabase
      .from('chips')
      .select('trust_score')
      .in('status', ['active', 'ready', 'warming'])
      .not('trust_score', 'is', null)

    const avgTrustScore =
      chipsData && chipsData.length > 0
        ? chipsData.reduce((sum, c) => sum + (Number(c.trust_score) || 0), 0) / chipsData.length
        : 0

    // Build trend data arrays
    const responseRateData: TrendDataPoint[] = []
    const latencyData2: TrendDataPoint[] = []
    const botDetectionData: TrendDataPoint[] = []
    const trustScoreData: TrendDataPoint[] = []

    dates.forEach((date) => {
      const metrics = metricsMap.get(date)
      if (metrics) {
        // Response rate: (respostas / enviadas) * 100
        const responseRate = metrics.enviadas > 0 ? (metrics.respostas / metrics.enviadas) * 100 : 0
        responseRateData.push({ date, value: Number(responseRate.toFixed(1)) })

        // Latency: average seconds
        const latency =
          metrics.latencia_count > 0 ? metrics.latencia_soma / metrics.latencia_count : 0
        latencyData2.push({ date, value: Number(latency.toFixed(1)) })

        // Bot detection rate: (detections / conversations) * 100
        const botRate =
          metrics.conversations > 0 ? (metrics.bot_detections / metrics.conversations) * 100 : 0
        botDetectionData.push({ date, value: Number(botRate.toFixed(2)) })

        // Trust score: use current average (no historical data available)
        trustScoreData.push({ date, value: Number(avgTrustScore.toFixed(1)) })
      }
    })

    // Calculate trends
    const calculateTrend = (data: TrendDataPoint[]): 'up' | 'down' | 'stable' => {
      if (data.length < 2) return 'stable'
      const first = data[0]?.value ?? 0
      const last = data[data.length - 1]?.value ?? 0
      const diff = last - first
      if (Math.abs(diff) < 0.5) return 'stable'
      return diff > 0 ? 'up' : 'down'
    }

    const getLastValue = (data: TrendDataPoint[]): number => {
      return data[data.length - 1]?.value ?? 0
    }

    const metrics = [
      {
        id: 'responseRate',
        label: 'Taxa de Resposta',
        data: responseRateData,
        currentValue: getLastValue(responseRateData),
        unit: '%',
        trend: calculateTrend(responseRateData),
        trendIsGood: calculateTrend(responseRateData) === 'up',
      },
      {
        id: 'latency',
        label: 'Latencia Media',
        data: latencyData2,
        currentValue: getLastValue(latencyData2),
        unit: 's',
        trend: calculateTrend(latencyData2),
        trendIsGood: calculateTrend(latencyData2) === 'down', // menor e melhor
      },
      {
        id: 'botDetection',
        label: 'Deteccao Bot',
        data: botDetectionData,
        currentValue: getLastValue(botDetectionData),
        unit: '%',
        trend: calculateTrend(botDetectionData),
        trendIsGood: calculateTrend(botDetectionData) === 'down', // menor e melhor
      },
      {
        id: 'trustScore',
        label: 'Trust Score Medio',
        data: trustScoreData,
        currentValue: getLastValue(trustScoreData),
        unit: '',
        trend: calculateTrend(trustScoreData),
        trendIsGood: calculateTrend(trustScoreData) === 'up',
      },
    ]

    return NextResponse.json({
      metrics,
      period: `${days}d`,
    })
  } catch (error) {
    console.error('Error fetching trends:', error)
    return NextResponse.json({ error: 'Failed to fetch trends' }, { status: 500 })
  }
}
