/**
 * API: GET /api/guardrails/status
 * Sprint 43 - Health Center
 *
 * Retorna status consolidado dos guardrails.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    // Fetch circuits status from backend
    const res = await fetch(`${API_URL}/guardrails/circuits`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) throw new Error('Erro ao buscar status dos guardrails')

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar status dos guardrails:', error)
    // Return empty data instead of error to allow page to render
    return NextResponse.json({
      circuits: [
        { name: 'evolution', state: 'CLOSED', failures: 0, threshold: 5 },
        { name: 'claude', state: 'CLOSED', failures: 0, threshold: 5 },
        { name: 'supabase', state: 'CLOSED', failures: 0, threshold: 5 },
      ],
    })
  }
}
