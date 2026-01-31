/**
 * API: GET/POST /api/admin/sugestoes
 * Sprint 43 - Qualidade
 *
 * Lista e cria sugestoes de prompt.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const params = searchParams.toString()

    const res = await fetch(`${API_URL}/admin/sugestoes${params ? `?${params}` : ''}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao buscar sugestoes')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar sugestoes:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao buscar sugestoes' },
      { status: 500 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const res = await fetch(`${API_URL}/admin/sugestoes`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao criar sugestao')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao criar sugestao:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao criar sugestao' },
      { status: 500 }
    )
  }
}
