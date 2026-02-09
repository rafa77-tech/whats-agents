/**
 * API: POST /api/conversas/[id]/feedback
 *
 * Registra feedback em mensagem da Julia.
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
    const { interacao_id, feedback_type, comment } = body as {
      interacao_id: number
      feedback_type: string
      comment?: string
    }

    if (!interacao_id || !feedback_type) {
      return NextResponse.json(
        { error: 'interacao_id e feedback_type obrigatorios' },
        { status: 400 }
      )
    }

    if (!['positive', 'negative'].includes(feedback_type)) {
      return NextResponse.json(
        { error: 'feedback_type deve ser "positive" ou "negative"' },
        { status: 400 }
      )
    }

    const response = await fetch(`${API_URL}/dashboard/conversations/${id}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ interacao_id, feedback_type, comment }),
    })

    const result = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail || 'Erro ao registrar feedback' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao registrar feedback:', error)
    return NextResponse.json({ error: 'Erro ao registrar feedback' }, { status: 500 })
  }
}
