/**
 * API: POST /api/conversas/[id]/send
 *
 * Envia uma mensagem manual em uma conversa (modo handoff).
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const body = await request.json()
    const { message } = body

    if (!message || typeof message !== 'string' || message.trim().length === 0) {
      return NextResponse.json({ error: 'Mensagem é obrigatória' }, { status: 400 })
    }

    const supabase = createAdminClient()

    // Get conversation to find cliente_id
    const { data: conversation, error: convError } = await supabase
      .from('conversations')
      .select('cliente_id, controlled_by')
      .eq('id', id)
      .single()

    if (convError || !conversation) {
      return NextResponse.json({ error: 'Conversa não encontrada' }, { status: 404 })
    }

    // Only allow sending if in handoff mode
    if (conversation.controlled_by !== 'human') {
      return NextResponse.json(
        { error: 'Só é possível enviar mensagens no modo handoff' },
        { status: 403 }
      )
    }

    // Create the message in interacoes
    const { data: interacao, error: msgError } = await supabase
      .from('interacoes')
      .insert({
        cliente_id: conversation.cliente_id,
        origem: 'dashboard',
        tipo: 'saida',
        canal: 'whatsapp',
        conteudo: message.trim(),
        autor_nome: 'Operador',
        autor_tipo: 'operador',
      })
      .select('id')
      .single()

    if (msgError) {
      console.error('Erro ao criar mensagem:', msgError)
      throw msgError
    }

    // Update conversation last_message_at
    await supabase
      .from('conversations')
      .update({
        last_message_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      })
      .eq('id', id)

    return NextResponse.json({ success: true, interacao_id: interacao?.id })
  } catch (error) {
    console.error('Erro ao enviar mensagem:', error)
    return NextResponse.json({ error: 'Erro ao enviar mensagem' }, { status: 500 })
  }
}
