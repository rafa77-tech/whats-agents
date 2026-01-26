/**
 * API: GET /api/dashboard/chips/instances/[name]/connection-state
 *
 * Verifica o estado da conexao de uma instancia.
 *
 * Sprint 40 - Instance Management UI
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ConnectionStateResponse {
  state: string
  connected: boolean
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ name: string }> }) {
  try {
    const { name } = await params

    if (!name) {
      return NextResponse.json({ error: 'Nome da instancia e obrigatorio' }, { status: 400 })
    }

    // Chamar backend Python
    const response = await fetch(
      `${API_URL}/chips/instances/${encodeURIComponent(name)}/connection-state`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      }
    )

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { error: errorData.detail || 'Falha ao verificar conexao' },
        { status: response.status }
      )
    }

    const data = (await response.json()) as ConnectionStateResponse

    return NextResponse.json({
      state: data.state,
      connected: data.connected,
    })
  } catch (error) {
    console.error('Error checking connection state:', error)
    return NextResponse.json({ error: 'Falha ao verificar conexao' }, { status: 500 })
  }
}
