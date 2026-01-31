/**
 * API: GET /api/admin/conversas
 * Sprint 43 - Qualidade
 *
 * Lista conversas para avaliacao.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const params = searchParams.toString()

    const res = await fetch(`${API_URL}/admin/conversas${params ? `?${params}` : ''}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar conversas')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar conversas:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar conversas' },
      { status: 500 }
    )
  }
}
