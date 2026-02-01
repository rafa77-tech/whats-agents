/**
 * API: GET /api/auditoria/export
 *
 * Exporta logs de auditoria em CSV.
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const params = new URLSearchParams()

    // Forward all query params
    searchParams.forEach((value, key) => {
      params.set(key, value)
    })

    const res = await fetch(`${API_URL}/dashboard/audit/export?${params.toString()}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) {
      throw new Error(`Backend returned ${res.status}`)
    }

    const blob = await res.blob()
    const today = new Date().toISOString().split('T')[0]

    return new NextResponse(blob, {
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename="audit_logs_${today}.csv"`,
      },
    })
  } catch (error) {
    console.error('Erro ao exportar logs de auditoria:', error)
    const today = new Date().toISOString().split('T')[0]
    return new NextResponse('timestamp,action,actor_email,actor_role,details\n', {
      headers: {
        'Content-Type': 'text/csv',
        'Content-Disposition': `attachment; filename="audit_logs_${today}.csv"`,
      },
    })
  }
}
