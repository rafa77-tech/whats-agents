/**
 * API: POST /api/group-entry/schedule
 * Sprint 43 - Group Entry
 *
 * Agenda um link para processamento (recebe link_id no body).
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const res = await fetch(`${API_URL}/group-entry/schedule`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao agendar link')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao agendar link:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao agendar link' },
      { status: 500 }
    )
  }
}
