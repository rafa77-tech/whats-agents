/**
 * API: POST /api/group-entry/import/csv
 * Sprint 43 - Group Entry
 *
 * Importa links via CSV.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData()

    const res = await fetch(`${API_URL}/group-entry/import/csv`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      body: formData,
    })

    if (!res.ok) {
      const errorData = await res.json().catch(() => ({}))
      throw new Error(errorData.detail || 'Erro ao importar CSV')
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao importar CSV:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Erro ao importar CSV' },
      { status: 500 }
    )
  }
}
