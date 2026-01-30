/**
 * API: GET /api/dashboard/conversations/[id]/messages
 *
 * Retorna as mensagens de uma conversa específica.
 *
 * Query params:
 * - limit: número máximo de mensagens (default: 20)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

interface MessageRow {
  id: string
  tipo: 'entrada' | 'saida'
  conteudo: string
  created_at: string
  delivery_status: string | null
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const supabase = await createClient()
    const { id } = await params
    const searchParams = request.nextUrl.searchParams
    const limit = parseInt(searchParams.get('limit') || '20')

    // Buscar mensagens da conversa
    const { data: messages, error } = await supabase
      .from('interacoes')
      .select('id, tipo, conteudo, created_at, delivery_status')
      .eq('conversation_id', id)
      .order('created_at', { ascending: true })
      .limit(limit)

    if (error) throw error

    const typedMessages = (messages as unknown as MessageRow[] | null) || []

    // Formatar para o frontend
    const formattedMessages = typedMessages.map((msg) => ({
      id: msg.id,
      tipo: msg.tipo,
      conteudo: msg.conteudo || '',
      timestamp: msg.created_at,
      deliveryStatus: msg.delivery_status,
      isFromJulia: msg.tipo === 'saida',
    }))

    return NextResponse.json({
      conversationId: id,
      messages: formattedMessages,
      total: formattedMessages.length,
    })
  } catch (error) {
    console.error('Error fetching conversation messages:', error)
    return NextResponse.json({ error: 'Failed to fetch messages' }, { status: 500 })
  }
}
