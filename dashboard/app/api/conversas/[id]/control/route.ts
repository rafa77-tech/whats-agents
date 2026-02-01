/**
 * API: POST /api/conversas/[id]/control
 *
 * Alterna o controle da conversa entre Julia e humano.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await request.json()
    const { controlled_by } = body

    if (!['ai', 'human'].includes(controlled_by)) {
      return NextResponse.json(
        { error: 'controlled_by deve ser "ai" ou "human"' },
        { status: 400 }
      )
    }

    const supabase = createAdminClient()

    const { error } = await supabase
      .from('conversations')
      .update({
        controlled_by,
        updated_at: new Date().toISOString(),
      })
      .eq('id', id)

    if (error) {
      console.error('Erro ao atualizar controle:', error)
      throw error
    }

    return NextResponse.json({ success: true, controlled_by })
  } catch (error) {
    console.error('Erro ao atualizar controle:', error)
    return NextResponse.json({ error: 'Erro ao atualizar controle' }, { status: 500 })
  }
}
