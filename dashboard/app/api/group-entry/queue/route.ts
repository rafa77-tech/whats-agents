/**
 * API: GET /api/group-entry/queue
 * Sprint 43 - Group Entry
 *
 * Lista fila de processamento.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/group-entry/queue`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar fila')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar fila:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar fila' },
      { status: 500 }
    )
  }
}
