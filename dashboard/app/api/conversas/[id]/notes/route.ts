/**
 * API: GET/POST /api/conversas/[id]/notes
 *
 * Gerencia notas do supervisor.
 * Sprint 54: Supervision Actions
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

    const response = await fetch(`${API_URL}/dashboard/conversations/${id}/notes`)
    const result = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail || 'Erro ao buscar notas' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao buscar notas:', error)
    return NextResponse.json({ error: 'Erro ao buscar notas' }, { status: 500 })
  }
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params
    const body = await request.json()
    const { content } = body as { content: string }

    if (!content?.trim()) {
      return NextResponse.json({ error: 'Conteudo obrigatorio' }, { status: 400 })
    }

    const response = await fetch(`${API_URL}/dashboard/conversations/${id}/notes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ content }),
    })

    const result = await response.json()

    if (!response.ok) {
      return NextResponse.json(
        { error: result.detail || 'Erro ao criar nota' },
        { status: response.status }
      )
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao criar nota:', error)
    return NextResponse.json({ error: 'Erro ao criar nota' }, { status: 500 })
  }
}
