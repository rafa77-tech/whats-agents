/**
 * API: DELETE /api/group-entry/queue/[id]
 * Sprint 43 - Group Entry
 *
 * Remove/cancela um item da fila.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params

    const res = await fetch(`${API_URL}/group-entry/queue/${id}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao cancelar item')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao cancelar item:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao cancelar item' },
      { status: 500 }
    )
  }
}
