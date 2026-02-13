/**
 * API: DELETE /api/dashboard/chips/instances/[name]/delete
 *
 * Deleta uma instancia WhatsApp permanentemente.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function DELETE(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await params

    if (!name) {
      return NextResponse.json({ error: 'Nome da instancia e obrigatorio' }, { status: 400 })
    }

    const response = await fetch(`${API_URL}/chips/instances/${encodeURIComponent(name)}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { error: errorData.detail || 'Falha ao deletar instancia' },
        { status: response.status }
      )
    }

    const data = await response.json()

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error deleting instance:', error)
    return NextResponse.json({ error: 'Falha ao deletar instancia' }, { status: 500 })
  }
}
