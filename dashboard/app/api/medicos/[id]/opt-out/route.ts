/**
 * API: POST /api/medicos/[id]/opt-out
 *
 * Toggle opt-out do médico.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const body = await request.json()
    const { opt_out } = body

    if (typeof opt_out !== 'boolean') {
      return NextResponse.json({ error: 'opt_out deve ser booleano' }, { status: 400 })
    }

    const supabase = createAdminClient()

    const updateData: Record<string, unknown> = {
      opt_out,
      updated_at: new Date().toISOString(),
    }

    if (opt_out) {
      updateData.opt_out_data = new Date().toISOString()
    }

    const { error } = await supabase.from('clientes').update(updateData).eq('id', id)

    if (error) {
      console.error('Erro ao atualizar opt-out:', error)
      throw error
    }

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao atualizar opt-out:', error)
    return NextResponse.json({ error: 'Erro ao atualizar opt-out' }, { status: 500 })
  }
}
