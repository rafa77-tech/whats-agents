/**
 * API: POST /api/conversas/[id]/channel/[instructionId]
 *
 * Confirm or reject instruction preview.
 * Sprint 54: Supervisor Channel
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string; instructionId: string }> }
): Promise<NextResponse> {
  try {
    const { id, instructionId } = await params
    const body = await request.json()
    const { action } = body as { action: 'confirm' | 'reject' }

    if (!['confirm', 'reject'].includes(action)) {
      return NextResponse.json({ error: 'action deve ser "confirm" ou "reject"' }, { status: 400 })
    }

    const response = await fetch(
      `${API_URL}/supervisor/channel/${id}/instruct/${instructionId}/${action}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      }
    )

    const result = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail || `Erro ao ${action} instrucao` },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao processar instrucao:', error)
    return NextResponse.json({ error: 'Erro ao processar instrucao' }, { status: 500 })
  }
}
