/**
 * API: /api/incidents
 * Sprint 55 E03 - Health Incidents
 *
 * Proxy para endpoints de incidentes no backend.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '20'
    const status = searchParams.get('status')
    const since = searchParams.get('since')

    const params = new URLSearchParams()
    params.set('limit', limit)
    if (status) params.set('status', status)
    if (since) params.set('since', since)

    const res = await fetch(`${API_URL}/incidents?${params.toString()}`, {
      headers: { Authorization: `Bearer ${process.env.API_SECRET ?? ''}` },
      cache: 'no-store',
    })

    if (!res.ok) {
      return NextResponse.json({ incidents: [], error: 'Backend error' }, { status: res.status })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error fetching incidents:', error)
    return NextResponse.json({ incidents: [], error: 'Failed to fetch incidents' }, { status: 500 })
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const res = await fetch(`${API_URL}/incidents`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      return NextResponse.json({ success: false, error: 'Backend error' }, { status: res.status })
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error registering incident:', error)
    return NextResponse.json(
      { success: false, error: 'Failed to register incident' },
      { status: 500 }
    )
  }
}
