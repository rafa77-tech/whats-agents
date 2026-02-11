/**
 * API: POST /api/dashboard/chips/[id]/errors/clear
 *
 * Limpa os erros de um chip (reseta contador e remove interacoes de erro).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id: chipId } = await params
    const supabase = await createClient()

    // 1. Resetar contador de erros no chip
    const { error: updateError } = await supabase
      .from('chips')
      .update({
        erros_ultimas_24h: 0,
        ultimo_erro_em: null,
        ultimo_erro_codigo: null,
        ultimo_erro_msg: null,
      })
      .eq('id', chipId)

    if (updateError) throw updateError

    // 2. Marcar interacoes de erro como resolvidas (soft delete via metadata)
    const oneDayAgo = new Date()
    oneDayAgo.setDate(oneDayAgo.getDate() - 1)

    const { error: interactionsError } = await supabase
      .from('chip_interactions')
      .update({
        metadata: {
          cleared_at: new Date().toISOString(),
          cleared_by: 'dashboard',
        },
      })
      .eq('chip_id', chipId)
      .eq('sucesso', false)
      .gte('created_at', oneDayAgo.toISOString())

    if (interactionsError) {
      console.warn('Error clearing interactions:', interactionsError)
      // Nao falhar por isso - o contador ja foi resetado
    }

    return NextResponse.json({
      success: true,
      message: 'Erros limpos com sucesso',
    })
  } catch (error) {
    console.error('Error clearing chip errors:', error)
    return NextResponse.json({ error: 'Failed to clear chip errors' }, { status: 500 })
  }
}
