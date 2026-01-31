/**
 * API: GET /api/group-entry/capacity
 * Sprint 43 - Group Entry
 *
 * Capacidade total de grupos.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/group-entry/capacity`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar capacidade')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar capacidade:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar capacidade' },
      { status: 500 }
    )
  }
}
