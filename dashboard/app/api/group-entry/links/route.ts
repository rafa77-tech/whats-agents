/**
 * API: GET /api/group-entry/links
 * Sprint 43 - Group Entry
 *
 * Lista links de grupos com filtros.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const params = searchParams.toString()

    const res = await fetch(`${API_URL}/group-entry/links${params ? `?${params}` : ''}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar links')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar links:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar links' },
      { status: 500 }
    )
  }
}
