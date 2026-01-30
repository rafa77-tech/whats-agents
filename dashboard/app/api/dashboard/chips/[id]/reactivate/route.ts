/**
 * API: POST /api/dashboard/chips/[id]/reactivate
 *
 * Reativa um chip banido ou cancelado.
 *
 * Sprint 41 - Chip Reactivation
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface ReactivateRequest {
  motivo: string
  para_status?: 'pending' | 'ready'
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: chipId } = await params
    const body = (await request.json()) as ReactivateRequest

    if (!body.motivo) {
      return NextResponse.json({ error: 'Motivo e obrigatorio' }, { status: 400 })
    }

    // Chamar backend Python
    const response = await fetch(`${API_URL}/chips/${chipId}/reactivate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        motivo: body.motivo,
        para_status: body.para_status || 'pending',
      }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { success: false, message: errorData.detail || 'Falha ao reativar chip' },
        { status: response.status }
      )
    }

    const data = await response.json()

    return NextResponse.json({
      success: true,
      message: data.message || 'Chip reativado com sucesso',
      chip: data,
    })
  } catch (error) {
    console.error('Error reactivating chip:', error)
    return NextResponse.json({ success: false, message: 'Falha ao reativar chip' }, { status: 500 })
  }
}
