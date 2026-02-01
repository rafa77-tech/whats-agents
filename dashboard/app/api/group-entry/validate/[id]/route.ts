/**
 * API: POST /api/group-entry/validate/[id]
 * Sprint 43 - Group Entry
 *
 * Valida um link individual.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params

    const res = await fetch(`${API_URL}/group-entry/validate/${id}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao validar link')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao validar link:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao validar link' },
      { status: 500 }
    )
  }
}
