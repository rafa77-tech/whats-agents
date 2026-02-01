/**
 * API: GET /api/admin/validacao/metricas
 * Sprint 43 - Qualidade
 *
 * Metricas do validador de output.
 */

import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/admin/validacao/metricas`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar metricas de validacao')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar metricas de validacao:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar metricas de validacao' },
      { status: 500 }
    )
  }
}
