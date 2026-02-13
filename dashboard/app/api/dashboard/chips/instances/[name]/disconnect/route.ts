/**
 * API: POST /api/dashboard/chips/instances/[name]/disconnect
 *
 * Desconecta (logout) uma instancia WhatsApp sem deletar.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await params

    if (!name) {
      return NextResponse.json({ error: 'Nome da instancia e obrigatorio' }, { status: 400 })
    }

    const response = await fetch(
      `${API_URL}/chips/instances/${encodeURIComponent(name)}/disconnect`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { error: errorData.detail || 'Falha ao desconectar instancia' },
        { status: response.status }
      )
    }

    const data = await response.json()

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error disconnecting instance:', error)
    return NextResponse.json({ error: 'Falha ao desconectar instancia' }, { status: 500 })
  }
}
