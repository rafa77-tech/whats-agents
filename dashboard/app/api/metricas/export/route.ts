/**
 * API: GET /api/metricas/export
 *
 * Exporta metricas em CSV.
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

    const res = await fetch(`${API_URL}/dashboard/metrics/export?${params.toString()}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) {
      // Se o backend nao tiver o endpoint, retornar CSV vazio
      const today = new Date().toISOString().split('T')[0]
      return NextResponse.json({
        content: 'data,mensagens,conversoes\n',
        filename: `metricas-${today}.csv`,
      })
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao exportar metricas:', error)
    const today = new Date().toISOString().split('T')[0]
    return NextResponse.json({
      content: 'data,mensagens,conversoes\n',
      filename: `metricas-${today}.csv`,
    })
  }
}
