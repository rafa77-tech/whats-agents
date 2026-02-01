/**
 * API: POST /api/guardrails/circuits/[name]/reset
 * Sprint 43 - Health Center
 *
 * Reseta um circuit breaker especifico.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await params
    const body = await request.json()

    const res = await fetch(`${API_URL}/guardrails/circuits/${name}/reset`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao resetar circuit breaker')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao resetar circuit breaker:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao resetar circuit breaker' },
      { status: 500 }
    )
  }
}
