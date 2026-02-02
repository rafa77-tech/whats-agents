/**
 * API: GET /api/conversas/[id]
 *
 * Retorna detalhes de uma conversa específica com mensagens.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

interface InteracaoRow {
  id: number
  conteudo: string | null
  autor_tipo: string | null
  autor_nome: string | null
  created_at: string | null
}

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const { id } = await params
    const supabase = createAdminClient()

    // Fetch conversation with client info
    const { data: conversation, error: convError } = await supabase
      .from('conversations')
      .select(
        `
        id,
        status,
        controlled_by,
        cliente_id,
        clientes!inner(id, primeiro_nome, sobrenome, telefone)
      `
      )
      .eq('id', id)
      .single()

    if (convError) {
      if (convError.code === 'PGRST116') {
        return NextResponse.json({ error: 'Conversa nao encontrada' }, { status: 404 })
      }
      console.error('Erro ao buscar conversa:', convError)
      throw convError
    }

    const cliente = conversation.clientes as unknown as {
      id: string
      primeiro_nome: string | null
      sobrenome: string | null
      telefone: string
    } | null

    // Fetch messages (interacoes) for this conversation
    // Buscar por conversation_id (coluna correta na tabela interacoes)
    const { data: interacoes, error: msgError } = await supabase
      .from('interacoes')
      .select(
        `
        id,
        conteudo,
        autor_tipo,
        autor_nome,
        created_at
      `
      )
      .eq('conversation_id', id)
      .order('created_at', { ascending: true })
      .limit(100)

    if (msgError) {
      console.error('Erro ao buscar mensagens:', msgError)
      // Continue without messages
    }

    // Transform messages to expected format for MessageBubble component
    const messages = ((interacoes as InteracaoRow[] | null) || []).map((msg) => ({
      id: String(msg.id),
      tipo: msg.autor_tipo === 'medico' ? 'entrada' : 'saida',
      conteudo: msg.conteudo || '',
      created_at: msg.created_at || new Date().toISOString(),
    }))

    const result = {
      id: conversation.id,
      status: conversation.status || 'active',
      controlled_by: conversation.controlled_by || 'julia',
      cliente: {
        id: cliente?.id || '',
        nome: cliente
          ? [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ') || 'Sem nome'
          : 'Desconhecido',
        telefone: cliente?.telefone || '',
      },
      messages,
    }

    return NextResponse.json(result)
  } catch (error) {
    console.error('Erro ao buscar conversa:', error)
    return NextResponse.json({ error: 'Erro ao buscar conversa' }, { status: 500 })
  }
}
