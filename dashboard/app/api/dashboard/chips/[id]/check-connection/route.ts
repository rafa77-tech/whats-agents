/**
 * API: GET /api/dashboard/chips/[id]/check-connection
 *
 * Verifica estado de conexão de um chip na Evolution API.
 *
 * Sprint 41 - Connection Detection
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: chipId } = await params

    // Chamar backend Python
    const response = await fetch(`${API_URL}/chips/${chipId}/check-connection`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { success: false, message: errorData.detail || 'Falha ao verificar conexão' },
        { status: response.status }
      )
    }

    const data = await response.json()

    return NextResponse.json({
      success: true,
      ...data,
    })
  } catch (error) {
    console.error('Error checking connection:', error)
    return NextResponse.json(
      { success: false, message: 'Falha ao verificar conexão' },
      { status: 500 }
    )
  }
}
