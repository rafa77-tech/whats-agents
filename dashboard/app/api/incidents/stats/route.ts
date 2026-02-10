/**
 * API: GET /api/incidents/stats
 * Sprint 55 E03 - Health Incidents
 *
 * Proxy para estatísticas de incidentes.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const dias = searchParams.get('dias') || '30'

    const res = await fetch(`${API_URL}/incidents/stats?dias=${dias}`, {
      headers: { Authorization: `Bearer ${process.env.API_SECRET ?? ''}` },
      cache: 'no-store',
    })

    if (!res.ok) {
      return NextResponse.json(
        {
          total_incidents: 0,
          critical_incidents: 0,
          degraded_incidents: 0,
          mttr_seconds: 0,
          uptime_percent: 100,
          error: 'Backend error',
        },
        { status: res.status }
      )
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching incident stats:', error)
    return NextResponse.json(
      {
        total_incidents: 0,
        critical_incidents: 0,
        degraded_incidents: 0,
        mttr_seconds: 0,
        uptime_percent: 100,
        error: 'Failed to fetch stats',
      },
      { status: 500 }
    )
  }
}
