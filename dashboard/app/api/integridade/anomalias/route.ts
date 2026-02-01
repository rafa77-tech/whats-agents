/**
 * API: GET /api/integridade/anomalias
 * Sprint 43 - Integridade
 *
 * Retorna lista de anomalias do sistema.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const limit = searchParams.get('limit') || '20'
    const offset = searchParams.get('offset') || '0'
    const resolvidas = searchParams.get('resolvidas') || 'false'

    const queryParams = new URLSearchParams({
      limit,
      offset,
      resolvidas,
    })

    const res = await fetch(`${API_URL}/integridade/anomalias?${queryParams}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) throw new Error('Erro ao buscar anomalias')

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar anomalias:', error)
    // Return empty list when backend is unavailable
    return NextResponse.json({
      anomalias: [],
      total: 0,
      total_abertas: 0,
      total_resolvidas: 0,
    })
  }
}
