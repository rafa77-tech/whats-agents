/**
 * API: POST /api/group-entry/process
 * Sprint 43 - Group Entry
 *
 * Processa fila de entrada.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST() {
  try {
    const res = await fetch(`${API_URL}/group-entry/process`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao processar fila')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao processar fila:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao processar fila' },
      { status: 500 }
    )
  }
}
