/**
 * API: POST /api/conversas/[id]/control
 *
 * Alterna o controle da conversa entre Julia e humano.
 * Chama o backend Python para atualizar.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await request.json()
    const { controlled_by } = body

    if (!['ai', 'human'].includes(controlled_by)) {
      return NextResponse.json({ error: 'controlled_by deve ser "ai" ou "human"' }, { status: 400 })
    }

    // Call Python backend
    const response = await fetch(`${API_URL}/dashboard/conversations/${id}/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ controlled_by }),
    })

    const result = await response.json()

    if (!response.ok) {
      console.error('Backend error:', result)
      return NextResponse.json(
        { error: result.detail || 'Erro ao atualizar controle' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao atualizar controle:', error)
    return NextResponse.json({ error: 'Erro ao atualizar controle' }, { status: 500 })
  }
}
