import { NextResponse } from 'next/server'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET() {
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
