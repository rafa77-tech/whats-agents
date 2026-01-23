import { NextResponse } from 'next/server'
import { shouldUseMock, mockSistemaStatus } from '@/lib/mock'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
  // Return mock data for E2E tests
  if (shouldUseMock()) {
    return NextResponse.json(mockSistemaStatus)
  }

  try {
    // Chamar backend Python para obter status
    const res = await fetch(`${API_URL}/sistema/status`, {
      headers: {
        Authorization: `Bearer ${process.env.API_SECRET ?? ''}`,
      },
      cache: 'no-store',
    })

    if (!res.ok) throw new Error('Erro ao buscar status')

    const data: unknown = await res.json()
    return NextResponse.json(data)
  } catch (error) {
    console.error('Erro ao buscar status do sistema:', error)
    return NextResponse.json(
      { error: 'Erro ao buscar status do sistema. Backend indisponivel.' },
      { status: 503 }
    )
  }
}
