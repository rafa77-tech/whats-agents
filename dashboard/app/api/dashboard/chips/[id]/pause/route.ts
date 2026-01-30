/**
 * API: POST /api/dashboard/chips/[id]/pause
 *
 * Pausa um chip.
 *
 * Sprint 36 - Chip Management
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: chipId } = await params

    // Chamar backend Python
    const response = await fetch(`${API_URL}/chips/${chipId}/pause`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { success: false, message: errorData.detail || 'Falha ao pausar chip' },
        { status: response.status }
      )
    }

    const data = await response.json()

    return NextResponse.json({
      success: true,
      message: 'Chip pausado com sucesso',
      chip: data,
    })
  } catch (error) {
    console.error('Error pausing chip:', error)
    return NextResponse.json({ success: false, message: 'Falha ao pausar chip' }, { status: 500 })
  }
}
