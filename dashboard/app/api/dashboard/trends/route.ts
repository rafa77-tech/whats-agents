/**
 * API: GET /api/dashboard/trends
 *
 * Returns sparkline data for key metrics over the selected period.
 *
 * Query params:
 * - period: "7d", "14d", or "30d" (default: "7d")
 */

import { NextRequest, NextResponse } from 'next/server'

interface TrendDataPoint {
  date: string
  value: number
}

function getLastValue(data: TrendDataPoint[]): number {
  const lastItem = data.at(-1)
  return lastItem?.value ?? 0
}

export async function GET(request: NextRequest) {
  try {
    // NOTE: createClient commented out until real metrics tables are available
    // const supabase = await createClient();
    const period = request.nextUrl.searchParams.get('period') || '7d'
    const days = parseInt(period) || 7

    // Gerar array de datas
    const dates: string[] = []
    for (let i = days - 1; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      const dateStr = date.toISOString().split('T')[0] ?? ''
      dates.push(dateStr)
    }

    // Buscar metricas por dia
    // NOTA: Isso requer tabelas de metricas agregadas por dia
    // Implementacao simplificada com dados simulados
    // TODO: Implementar busca real quando tabelas de metricas diarias estiverem disponiveis

    const generateTrendData = (
      baseValue: number,
      variance: number,
      trend: 'up' | 'down' | 'stable'
    ): TrendDataPoint[] => {
      // Use seeded random for consistent values per day
      return dates.map((date, i) => {
        const progress = dates.length > 1 ? i / (dates.length - 1) : 0
        const trendOffset =
          trend === 'up' ? progress * variance : trend === 'down' ? -progress * variance : 0
        // Create deterministic variation based on date
        const dateSeed = date.split('-').reduce((a, b) => a + parseInt(b), 0)
        const deterministicOffset = ((dateSeed % 10) / 10 - 0.5) * variance * 0.5
        return {
          date,
          value: baseValue + trendOffset + deterministicOffset,
        }
      })
    }

    const responseRateData = generateTrendData(30, 5, 'up')
    const latencyData = generateTrendData(28, 6, 'down')
    const botDetectionData = generateTrendData(0.6, 0.3, 'down')
    const trustScoreData = generateTrendData(80, 5, 'up')

    const metrics = [
      {
        id: 'responseRate',
        label: 'Taxa de Resposta',
        data: responseRateData,
        currentValue: getLastValue(responseRateData),
        unit: '%',
        trend: 'up' as const,
        trendIsGood: true,
      },
      {
        id: 'latency',
        label: 'Latencia Media',
        data: latencyData,
        currentValue: getLastValue(latencyData),
        unit: 's',
        trend: 'down' as const,
        trendIsGood: true, // menor e melhor
      },
      {
        id: 'botDetection',
        label: 'Deteccao Bot',
        data: botDetectionData,
        currentValue: getLastValue(botDetectionData),
        unit: '%',
        trend: 'down' as const,
        trendIsGood: true, // menor e melhor
      },
      {
        id: 'trustScore',
        label: 'Trust Score Medio',
        data: trustScoreData,
        currentValue: getLastValue(trustScoreData),
        unit: '',
        trend: 'up' as const,
        trendIsGood: true,
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
