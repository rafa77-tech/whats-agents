/**
 * API: GET /api/dashboard/chips/instances/[name]/qr-code
 *
 * Obtem QR code para pareamento da instancia.
 *
 * Sprint 40 - Instance Management UI
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface QRCodeResponse {
  qr_code: string | null
  code: string | null
  state: string
  pairing_code: string | null
}

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ name: string }> }
) {
  try {
    const { name } = await params

    if (!name) {
      return NextResponse.json({ error: 'Nome da instancia e obrigatorio' }, { status: 400 })
    }

    // Chamar backend Python
    const response = await fetch(`${API_URL}/chips/instances/${encodeURIComponent(name)}/qr-code`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { error: errorData.detail || 'Falha ao obter QR code' },
        { status: response.status }
      )
    }

    const data = (await response.json()) as QRCodeResponse

    return NextResponse.json({
      qrCode: data.qr_code,
      code: data.code,
      state: data.state,
      pairingCode: data.pairing_code,
    })
  } catch (error) {
    console.error('Error getting QR code:', error)
    return NextResponse.json({ error: 'Falha ao obter QR code' }, { status: 500 })
  }
}
