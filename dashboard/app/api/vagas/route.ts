/**
 * API: GET /api/vagas
 *
 * Proxy para listagem de vagas do backend Python.
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

    const res = await fetch(`${API_URL}/dashboard/shifts?${params.toString()}`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) {
      if (res.status === 404) {
        return NextResponse.json({ data: [], total: 0, pages: 0 })
      }
      throw new Error(`Backend returned ${res.status}`)
    }

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar vagas:', error)
    return NextResponse.json({ data: [], total: 0, pages: 0 })
  }
}
