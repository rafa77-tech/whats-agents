/**
 * API: POST /api/admin/avaliacoes
 * Sprint 43 - Qualidade
 *
 * Salva avaliacao de conversa.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const res = await fetch(`${API_URL}/admin/avaliacoes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao salvar avaliacao')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao salvar avaliacao:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao salvar avaliacao' },
      { status: 500 }
    )
  }
}
