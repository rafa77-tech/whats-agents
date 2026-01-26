/**
 * API: POST /api/dashboard/chips/instances
 *
 * Cria uma nova instancia WhatsApp via Evolution API.
 *
 * Sprint 40 - Instance Management UI
 */

import { NextRequest, NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface CreateInstanceRequest {
  telefone: string
  instanceName?: string
}

interface CreateInstanceResponse {
  success: boolean
  instance_name: string
  chip_id: string
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as CreateInstanceRequest

    // Validar telefone
    if (!body.telefone) {
      return NextResponse.json({ error: 'Telefone e obrigatorio' }, { status: 400 })
    }

    // Limpar telefone (apenas digitos)
    const telefoneClean = body.telefone.replace(/\D/g, '')

    if (telefoneClean.length < 10 || telefoneClean.length > 13) {
      return NextResponse.json(
        { error: 'Telefone invalido. Use formato: 5511999999999' },
        { status: 400 }
      )
    }

    // Chamar backend Python
    const response = await fetch(`${API_URL}/chips/instances`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        telefone: telefoneClean,
        instance_name: body.instanceName,
      }),
    })

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Erro desconhecido' }))
      return NextResponse.json(
        { error: errorData.detail || 'Falha ao criar instancia' },
        { status: response.status }
      )
    }

    const data = (await response.json()) as CreateInstanceResponse

    return NextResponse.json({
      success: true,
      instanceName: data.instance_name,
      chipId: data.chip_id,
    })
  } catch (error) {
    console.error('Error creating instance:', error)
    return NextResponse.json({ error: 'Falha ao criar instancia' }, { status: 500 })
  }
}
