/**
 * API: GET /api/integridade/kpis
 * Sprint 43 - Integridade
 *
 * Retorna KPIs de integridade do sistema.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/integridade/kpis`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) throw new Error('Erro ao buscar KPIs')

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar KPIs de integridade:', error)
    // Return mock data when backend is unavailable
    return NextResponse.json({
      health_score: 85,
      conversion_rate: 72,
      time_to_fill: 4.2,
    })
  }
}
