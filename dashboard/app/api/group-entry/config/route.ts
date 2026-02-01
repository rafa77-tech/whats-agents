/**
 * API: GET/PATCH /api/group-entry/config
 * Sprint 43 - Group Entry
 *
 * Configuracao do Group Entry.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/group-entry/config`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar configuracao')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar configuracao:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar configuracao' },
      { status: 500 }
    )
  }
}

export async function PATCH(request: NextRequest) {
  try {
    const body = await request.json()

    const res = await fetch(`${API_URL}/group-entry/config`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao atualizar configuracao')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao atualizar configuracao:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao atualizar configuracao' },
      { status: 500 }
    )
  }
}
