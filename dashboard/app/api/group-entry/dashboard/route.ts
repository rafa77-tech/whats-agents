/**
 * API: GET /api/group-entry/dashboard
 * Sprint 43 - Group Entry
 *
 * Dados consolidados do Group Entry.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/group-entry/dashboard`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar dashboard')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar dashboard:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar dashboard' },
      { status: 500 }
    )
  }
}
