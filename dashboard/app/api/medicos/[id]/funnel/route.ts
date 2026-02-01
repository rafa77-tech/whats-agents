/**
 * API: PUT /api/medicos/[id]/funnel
 *
 * Atualiza o status do funil do médico.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function PUT(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await request.json()
    const { status } = body

    if (!status) {
      return NextResponse.json({ error: 'Status é obrigatório' }, { status: 400 })
    }

    const supabase = createAdminClient()

    const { error } = await supabase
      .from('clientes')
      .update({
        stage_jornada: status,
        updated_at: new Date().toISOString(),
      })
      .eq('id', id)

    if (error) {
      console.error('Erro ao atualizar funil:', error)
      throw error
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao atualizar funil:', error)
    return NextResponse.json({ error: 'Erro ao atualizar funil' }, { status: 500 })
  }
}
