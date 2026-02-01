/**
 * API: GET /api/health/rate-limit
 * Sprint 43 - Health Center
 *
 * Proxy para buscar estatisticas de rate limiting do backend Python.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/health/rate-limit`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) {
      throw new Error(`Backend returned ${res.status}`)
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar rate limit:', error)
    // Return fallback data on error
    return NextResponse.json({
      rate_limit: {
        hourly: { used: 0, limit: 20 },
        daily: { used: 0, limit: 100 },
      },
      error: true,
      timestamp: new Date().toISOString(),
    })
  }
}
