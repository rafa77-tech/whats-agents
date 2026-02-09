/**
 * API: GET/POST /api/conversas/[id]/channel
 *
 * Proxy para supervisor channel.
 * Sprint 54: Supervisor Channel
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params

    const response = await fetch(`${API_URL}/supervisor/channel/${id}/history`)
    const result = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail || 'Erro ao buscar historico' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao buscar historico channel:', error)
    return NextResponse.json({ error: 'Erro ao buscar historico' }, { status: 500 })
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params
    const body = await request.json()
    const { content, type: msgType } = body as { content: string; type?: string }

    if (!content?.trim()) {
      return NextResponse.json({ error: 'Conteudo obrigatorio' }, { status: 400 })
    }

    // Route to message or instruct based on type
    const endpoint =
      msgType === 'instruction'
        ? `${API_URL}/supervisor/channel/${id}/instruct`
        : `${API_URL}/supervisor/channel/${id}/message`

    const requestBody =
      msgType === 'instruction' ? { instruction: content } : { content }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(requestBody),
    })

    const result = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail || 'Erro ao enviar mensagem' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao enviar mensagem channel:', error)
    return NextResponse.json({ error: 'Erro ao enviar mensagem' }, { status: 500 })
  }
}
