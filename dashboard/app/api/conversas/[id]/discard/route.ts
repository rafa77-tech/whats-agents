/**
 * API: POST /api/conversas/[id]/discard
 *
 * Descarta um contato: marca como opted_out e arquiva a conversa.
 * Sprint 64: Descartar contato
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

const VALID_REASONS = ['Nao e medico', 'Spam/Bot', 'Numero errado', 'Outro']

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
): Promise<NextResponse> {
  try {
    const { id } = await params
    const body = await request.json()
    const { reason } = body as { reason: string }

    if (!reason?.trim()) {
      return NextResponse.json({ error: 'Motivo obrigatorio' }, { status: 400 })
    }

    if (!VALID_REASONS.includes(reason)) {
      return NextResponse.json({ error: 'Motivo invalido' }, { status: 400 })
    }

    const supabase = createAdminClient()

    // Fetch conversation to get cliente_id
    const { data: conversation, error: convError } = await supabase
      .from('conversations')
      .select('id, cliente_id')
      .eq('id', id)
      .single()

    if (convError) {
      if (convError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Conversa nao encontrada' }, { status: 404 })
      }
      console.error('Erro ao buscar conversa:', convError)
      throw convError
    }

    const now = new Date().toISOString()

    // Update cliente: mark as opted_out
    const { error: clienteError } = await supabase
      .from('clientes')
      .update({
        opted_out: true,
        opted_out_at: now,
        opted_out_reason: reason,
      })
      .eq('id', conversation.cliente_id)

    if (clienteError) {
      console.error('Erro ao atualizar cliente:', clienteError)
      throw clienteError
    }

    // Close conversation
    const { error: archiveError } = await supabase
      .from('conversations')
      .update({
        status: 'completed',
        controlled_by: 'ai',
      })
      .eq('id', id)

    if (archiveError) {
      console.error('Erro ao arquivar conversa:', archiveError)
      throw archiveError
    }

    // Register business event
    await supabase.from('business_events').insert({
      event_type: 'contact_discarded',
      source: 'dashboard',
      conversation_id: id,
      cliente_id: conversation.cliente_id,
      event_props: { reason },
      ts: now,
    })

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Erro ao descartar contato:', error)
    return NextResponse.json({ error: 'Erro ao descartar contato' }, { status: 500 })
  }
}
