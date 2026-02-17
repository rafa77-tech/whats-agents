import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import { mesclarHospitais } from '@/lib/hospitais'

export const dynamic = 'force-dynamic'

/**
 * POST /api/hospitais/[id]/merge
 * Mescla outro hospital neste (este é o principal)
 * Body: { duplicado_id: string }
 */
export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id: principalId } = await params
    const body = await request.json()

    const duplicadoId = typeof body.duplicado_id === 'string' ? body.duplicado_id.trim() : ''
    if (!duplicadoId) {
      return NextResponse.json({ detail: 'duplicado_id e obrigatorio' }, { status: 400 })
    }

    if (principalId === duplicadoId) {
      return NextResponse.json(
        { detail: 'Nao e possivel mesclar um hospital consigo mesmo' },
        { status: 400 }
      )
    }

    const supabase = createAdminClient()
    const result = await mesclarHospitais(supabase, principalId, duplicadoId, 'dashboard')

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao mesclar hospitais:', error)
    const message = error instanceof Error ? error.message : 'Erro interno do servidor'
    return NextResponse.json({ detail: message }, { status: 500 })
  }
}
