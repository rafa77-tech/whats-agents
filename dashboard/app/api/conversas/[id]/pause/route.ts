/**
 * API: POST /api/conversas/[id]/pause
 *
 * Pausa/retoma a Julia nesta conversa.
 * Sprint 54: Supervision Actions
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params
    const body = await request.json()
    const { action, motivo } = body as { action: string; motivo?: string }

    const endpoint = action === 'resume' ? 'resume' : 'pause'
    const payload = endpoint === 'pause' ? { motivo: motivo || null } : {}

    const response = await fetch(`${API_URL}/dashboard/conversations/${id}/${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    const result = await response.json()

    if (!response.ok) {
      console.error('Backend error:', result)
      return NextResponse.json(
        { error: result.detail || 'Erro ao pausar/retomar' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao pausar/retomar:', error)
    return NextResponse.json({ error: 'Erro ao pausar/retomar' }, { status: 500 })
  }
}
