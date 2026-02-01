/**
 * API: GET /api/metricas
 *
 * Proxy para metricas do backend Python.
 * Retorna KPIs, funil, tendencias e tempos de resposta.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const from = searchParams.get('from')
    const to = searchParams.get('to')

    const params = new URLSearchParams()
    if (from) params.set('from', from)
    if (to) params.set('to', to)

    const res = await fetch(`${API_URL}/dashboard/metrics?${params.toString()}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) {
      // Se o backend nao tiver o endpoint, retornar dados mock
      if (res.status === 404) {
        return NextResponse.json(getMockMetrics())
      }
      throw new Error(`Backend returned ${res.status}`)
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar metricas:', error)
    // Retornar dados mock em caso de erro
    return NextResponse.json(getMockMetrics())
  }
}

function getMockMetrics() {
  return {
    kpis: {
      total_messages: {
        label: 'Total Mensagens',
        value: '0',
        change: 0,
        changeLabel: 'vs periodo anterior',
      },
      active_doctors: {
        label: 'Medicos Ativos',
        value: '0',
        change: 0,
        changeLabel: 'vs periodo anterior',
      },
      conversion_rate: {
        label: 'Taxa Conversao',
        value: '0%',
        change: 0,
        changeLabel: 'vs periodo anterior',
      },
      avg_response_time: {
        label: 'Tempo Medio',
        value: '-',
        change: 0,
        changeLabel: 'vs periodo anterior',
      },
    },
    funnel: [
      { name: 'Enviadas', count: 0, percentage: 100, color: '#3b82f6' },
      { name: 'Entregues', count: 0, percentage: 0, color: '#22c55e' },
      { name: 'Lidas', count: 0, percentage: 0, color: '#eab308' },
      { name: 'Respondidas', count: 0, percentage: 0, color: '#f97316' },
      { name: 'Convertidas', count: 0, percentage: 0, color: '#ef4444' },
    ],
    trends: [],
    response_times: [],
  }
}
