/**
 * API: PATCH /api/admin/sugestoes/[id]
 * Sprint 43 - Qualidade
 *
 * Atualiza status de sugestao.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function PATCH(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const body = await request.json()

    const res = await fetch(`${API_URL}/admin/sugestoes/${id}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao atualizar sugestao')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao atualizar sugestao:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao atualizar sugestao' },
      { status: 500 }
    )
  }
}
