/**
 * API: GET /api/dashboard/chips/[id]/interactions
 *
 * Retorna interacoes recentes de um chip.
 * Sprint 39 - Chip Interactions
 * Sprint 64 - Resolve conversationId por telefone do destinatario
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'
import type { ChipInteractionsResponse, ChipInteraction, InteractionType } from '@/types/chips'

export const dynamic = 'force-dynamic'

interface InteractionRow {
  id: string
  tipo: string
  created_at: string
  metadata: Record<string, unknown> | null
  destinatario: string | null
  remetente: string | null
  erro_mensagem: string | null
  midia_tipo: string | null
  obteve_resposta: boolean | null
  tempo_resposta_segundos: number | null
}

function mapInteractionType(tipo: string): InteractionType {
  const typeMap: Record<string, InteractionType> = {
    msg_enviada: 'conversa_individual',
    msg_recebida: 'conversa_individual',
    warmup_msg: 'warmup_par',
    status_criado: 'midia_enviada',
    erro: 'erro',
    entrada_grupo: 'entrada_grupo',
    mensagem_grupo: 'mensagem_grupo',
  }
  return typeMap[tipo] || 'conversa_individual'
}

function getInteractionDescription(tipo: string, metadata: Record<string, unknown> | null): string {
  switch (tipo) {
    case 'msg_enviada':
      return 'Mensagem enviada'
    case 'msg_recebida':
      return 'Mensagem recebida'
    case 'warmup_msg':
      return 'Mensagem de warmup enviada'
    case 'status_criado':
      return 'Status/midia criado'
    case 'erro':
      return (metadata?.error as string) || 'Erro na operacao'
    case 'entrada_grupo':
      return 'Entrou em grupo'
    case 'mensagem_grupo':
      return 'Mensagem enviada em grupo'
    default:
      return `Interacao: ${tipo}`
  }
}

function isSuccessfulInteraction(tipo: string): boolean {
  return tipo !== 'erro'
}

/**
 * Resolve conversation IDs for a set of phone numbers.
 * Does a batch lookup: phone → clientes → conversations.
 */
async function resolveConversationsByPhone(
  supabase: Awaited<ReturnType<typeof createClient>>,
  phones: string[]
): Promise<Map<string, string>> {
  const phoneToConversation = new Map<string, string>()
  if (phones.length === 0) return phoneToConversation

  // Batch lookup: find clients by phone numbers
  const { data: clients } = await supabase
    .from('clientes')
    .select('id, telefone')
    .in('telefone', phones)

  if (!clients || clients.length === 0) return phoneToConversation

  const clientIds = clients.map((c: { id: string }) => c.id)
  const clientIdToPhone = new Map(
    clients.map((c: { id: string; telefone: string }) => [c.id, c.telefone])
  )

  // Find most recent conversation for each client
  const { data: conversations } = await supabase
    .from('conversations')
    .select('id, cliente_id')
    .in('cliente_id', clientIds)
    .order('last_message_at', { ascending: false })

  if (!conversations) return phoneToConversation

  // Map phone → first (most recent) conversation found
  for (const conv of conversations as { id: string; cliente_id: string }[]) {
    const phone = clientIdToPhone.get(conv.cliente_id)
    if (phone && !phoneToConversation.has(phone)) {
      phoneToConversation.set(phone, conv.id)
    }
  }

  return phoneToConversation
}

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  try {
    const supabase = await createClient()
    const { id: chipId } = await params
    const searchParams = request.nextUrl.searchParams

    const limit = parseInt(searchParams.get('limit') || '20', 10)
    const offset = parseInt(searchParams.get('offset') || '0', 10)
    const typeFilter = searchParams.get('type')

    // Verificar se chip existe
    const { data: chip, error: chipError } = await supabase
      .from('chips')
      .select('id')
      .eq('id', chipId)
      .single()

    if (chipError || !chip) {
      return NextResponse.json({ error: 'Chip not found' }, { status: 404 })
    }

    // Buscar total de interacoes
    let countQuery = supabase
      .from('chip_interactions')
      .select('id', { count: 'exact', head: true })
      .eq('chip_id', chipId)

    if (typeFilter) {
      countQuery = countQuery.eq('tipo', typeFilter)
    }

    const { count: totalCount } = await countQuery

    // Buscar interacoes com paginacao
    let query = supabase
      .from('chip_interactions')
      .select(
        'id, tipo, created_at, metadata, destinatario, remetente, erro_mensagem, midia_tipo, obteve_resposta, tempo_resposta_segundos'
      )
      .eq('chip_id', chipId)
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1)

    if (typeFilter) {
      query = query.eq('tipo', typeFilter)
    }

    const { data: interactions, error: interactionsError } = await query

    if (interactionsError) {
      console.error('Error fetching interactions:', interactionsError)
      return NextResponse.json({ error: 'Failed to fetch interactions' }, { status: 500 })
    }

    const rows = (interactions as InteractionRow[] | null) || []
    const total = totalCount ?? 0

    // Collect unique phone numbers to resolve conversations
    const phones = Array.from(
      new Set(
        rows
          .map((r) => r.destinatario || r.remetente)
          .filter((p): p is string => p !== null && p !== '')
      )
    )

    const phoneToConversation = await resolveConversationsByPhone(supabase, phones)

    const formattedInteractions: ChipInteraction[] = rows.map((row) => {
      const phone = row.destinatario || row.remetente
      const interaction: ChipInteraction = {
        id: row.id,
        type: mapInteractionType(row.tipo),
        timestamp: row.created_at,
        description: getInteractionDescription(row.tipo, row.metadata),
        success: isSuccessfulInteraction(row.tipo),
        destinatario: row.destinatario,
        remetente: row.remetente,
        erroMensagem: row.erro_mensagem,
        midiaTipo: row.midia_tipo,
        obteveResposta: row.obteve_resposta,
        tempoRespostaSegundos: row.tempo_resposta_segundos,
      }
      if (row.metadata) {
        interaction.metadata = row.metadata
      }
      if (phone && phoneToConversation.has(phone)) {
        interaction.conversationId = phoneToConversation.get(phone)!
      }
      return interaction
    })

    const response: ChipInteractionsResponse = {
      interactions: formattedInteractions,
      total,
      hasMore: offset + limit < total,
    }

    return NextResponse.json(response)
  } catch (error) {
    console.error('Error fetching chip interactions:', error)
    return NextResponse.json({ error: 'Failed to fetch chip interactions' }, { status: 500 })
  }
}
