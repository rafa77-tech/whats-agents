/**
 * API: GET /api/conversas
 *
 * Lista conversas com informações de chip, enrichment e categorização.
 * Sprint 64: Performance + server-side filtering + unread_count + attention_reason
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import type { SupervisionTab } from '@/types/conversas'

export const dynamic = 'force-dynamic'

const TWO_DAYS_MS = 48 * 60 * 60 * 1000
const ONE_HOUR_MS = 60 * 60 * 1000

function categorizeConversation(conv: {
  controlled_by: string
  status: string
  sentimento_score?: number | null | undefined
  last_message_direction?: string | null | undefined
  last_message_at?: string | null | undefined
  has_handoff?: boolean | undefined
}): SupervisionTab {
  if (conv.controlled_by === 'human' || conv.has_handoff) return 'atencao'
  if (conv.sentimento_score != null && conv.sentimento_score <= -2) return 'atencao'

  if (conv.last_message_direction === 'entrada' && conv.last_message_at) {
    const waitMs = Date.now() - new Date(conv.last_message_at).getTime()
    if (waitMs > ONE_HOUR_MS) return 'atencao'
  }

  if (['completed', 'archived', 'encerrada', 'arquivada'].includes(conv.status)) {
    return 'encerradas'
  }

  if (conv.last_message_direction === 'saida' && conv.controlled_by === 'ai') {
    return 'aguardando'
  }

  return 'julia_ativa'
}

function getAttentionReason(conv: {
  controlled_by: string
  has_handoff?: boolean | undefined
  handoff_reason?: string | undefined
  sentimento_score?: number | null | undefined
  last_message_direction?: string | null | undefined
  last_message_at?: string | null | undefined
}): string | null {
  if (conv.controlled_by === 'human' || conv.has_handoff) {
    return conv.handoff_reason || 'Handoff pendente'
  }

  if (conv.sentimento_score != null && conv.sentimento_score <= -2) {
    return 'Sentimento muito negativo'
  }

  if (conv.last_message_direction === 'entrada' && conv.last_message_at) {
    const waitMs = Date.now() - new Date(conv.last_message_at).getTime()
    if (waitMs > ONE_HOUR_MS) {
      const hours = Math.floor(waitMs / ONE_HOUR_MS)
      const mins = Math.floor((waitMs % ONE_HOUR_MS) / 60000)
      return `Sem resposta ha ${hours > 0 ? `${hours}h` : ''}${mins > 0 ? `${mins}min` : ''}`
    }
  }

  return null
}

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams
    const page = parseInt(searchParams.get('page') || '1')
    const perPage = parseInt(searchParams.get('per_page') || '50')
    const tab = searchParams.get('tab') as SupervisionTab | null
    const chipId = searchParams.get('chip_id')
    const search = searchParams.get('search')

    const supabase = createAdminClient()

    // Step 1: Get conversation IDs filtered by chip if needed
    let conversationIds: string[] | null = null

    if (chipId) {
      const { data: chipConversations } = await supabase
        .from('conversation_chips')
        .select('conversa_id')
        .eq('chip_id', chipId)
        .eq('active', true)

      conversationIds = chipConversations?.map((cc) => cc.conversa_id) || []

      if (conversationIds.length === 0) {
        return NextResponse.json({ data: [], total: 0, pages: 0 })
      }
    }

    // Step 2: Build main query with server-side tab pre-filtering
    let query = supabase.from('conversations').select(
      `
        id,
        status,
        controlled_by,
        message_count,
        last_message_at,
        created_at,
        cliente_id,
        clientes!inner(id, primeiro_nome, sobrenome, telefone, stage_jornada, especialidade)
      `,
      { count: 'exact' }
    )

    // Apply chip filter
    if (conversationIds) {
      query = query.in('id', conversationIds)
    }

    // Apply search filter
    if (search) {
      query = query.or(
        `clientes.primeiro_nome.ilike.%${search}%,clientes.sobrenome.ilike.%${search}%,clientes.telefone.ilike.%${search}%`
      )
    }

    // Server-side tab pre-filtering (SQL WHERE clauses)
    const twoDaysAgo = new Date(Date.now() - TWO_DAYS_MS).toISOString()
    if (tab === 'encerradas') {
      query = query
        .in('status', ['completed', 'archived', 'encerrada', 'arquivada'])
        .gte('updated_at', twoDaysAgo)
    } else if (tab === 'atencao') {
      // Atencao includes: human-controlled, handoffs, negative sentiment, long wait
      // We can filter controlled_by=human at SQL level, but sentiment/wait need enrichment
      // Fetch broader set: human + recent active conversations
      query = query.not('status', 'in', '("completed","archived","encerrada","arquivada")')
    } else if (tab === 'aguardando' || tab === 'julia_ativa') {
      query = query.eq('controlled_by', 'ai').eq('status', 'active')
    } else {
      // No tab: exclude very old completed
      query = query.or(`status.neq.completed,updated_at.gte.${twoDaysAgo}`)
    }

    query = query.order('last_message_at', { ascending: false, nullsFirst: false }).limit(500)

    const { data: conversations, error } = await query

    if (error) {
      console.error('Erro ao buscar conversas:', error)
      throw error
    }

    const conversaIds = (conversations || []).map((c) => c.id)

    if (conversaIds.length === 0) {
      return NextResponse.json({ data: [], total: 0, pages: 0 })
    }

    // Step 3: Parallel enrichment queries (optimized)
    const [chipLinksResult, lastMessagesResult, handoffsResult] = await Promise.all([
      // Chip info
      supabase
        .from('conversation_chips')
        .select(
          `
          conversa_id,
          chips!inner(id, telefone, instance_name, status, trust_level)
        `
        )
        .in('conversa_id', conversaIds)
        .eq('active', true),

      // Last message per conversation via DISTINCT ON (exactly 1 per conversation)
      supabase.rpc('get_last_messages', { conv_ids: conversaIds }),

      // Active handoffs
      supabase
        .from('handoffs')
        .select('conversation_id, motivo, status')
        .in('conversation_id', conversaIds)
        .eq('status', 'pendente'),
    ])

    // Step 4: Build enrichment maps
    const chipMap = new Map<
      string,
      { id: string; telefone: string; instance_name: string; status: string; trust_level: string }
    >()
    chipLinksResult.data?.forEach((link) => {
      const chip = link.chips as unknown as {
        id: string
        telefone: string
        instance_name: string
        status: string
        trust_level: string
      }
      if (chip) chipMap.set(link.conversa_id, chip)
    })

    // Map last messages (RPC returns exactly 1 per conversation via DISTINCT ON)
    const lastMessageMap = new Map<
      string,
      { conteudo: string; direction: 'entrada' | 'saida'; created_at: string }
    >()
    lastMessagesResult.data?.forEach(
      (msg: {
        conversation_id: string
        conteudo: string | null
        autor_tipo: string | null
        created_at: string | null
      }) => {
        lastMessageMap.set(msg.conversation_id, {
          conteudo: msg.conteudo || '',
          direction: msg.autor_tipo === 'medico' ? 'entrada' : 'saida',
          created_at: msg.created_at || '',
        })
      }
    )

    const handoffMap = new Map<string, string>()
    handoffsResult.data?.forEach((h) => {
      handoffMap.set(h.conversation_id, h.motivo || 'Handoff pendente')
    })

    // Step 5: Transform + categorize + compute unread_count + attention_reason
    let enrichedData = (conversations || []).map((c) => {
      const cliente = c.clientes as unknown as {
        id: string
        primeiro_nome: string | null
        sobrenome: string | null
        telefone: string
        stage_jornada?: string | null
        especialidade?: string | null
      } | null

      const clienteNome = cliente
        ? [cliente.primeiro_nome, cliente.sobrenome].filter(Boolean).join(' ') || 'Sem nome'
        : 'Desconhecido'

      const chip = chipMap.get(c.id)
      const lastMsg = lastMessageMap.get(c.id)
      const handoffReason = handoffMap.get(c.id)
      const hasHandoff = handoffMap.has(c.id)

      // unread_count: if last message is from doctor (entrada), count as 1 unread
      // More accurate than hardcoded 0
      const unreadCount = lastMsg?.direction === 'entrada' ? 1 : 0

      const enriched = {
        id: c.id,
        cliente_nome: clienteNome,
        cliente_telefone: cliente?.telefone || '',
        status: c.status || 'active',
        controlled_by: c.controlled_by || 'ai',
        last_message: lastMsg?.conteudo || undefined,
        last_message_at: c.last_message_at,
        last_message_direction: lastMsg?.direction || undefined,
        unread_count: unreadCount,
        chip: chip
          ? {
              id: chip.id,
              telefone: chip.telefone,
              instance_name: chip.instance_name,
              status: chip.status,
              trust_level: chip.trust_level,
            }
          : null,
        stage_jornada: cliente?.stage_jornada || undefined,
        especialidade: cliente?.especialidade || undefined,
        has_handoff: hasHandoff,
        handoff_reason: handoffReason || undefined,
        attention_reason: null as string | null,
      }

      // Compute attention reason for all conversations
      enriched.attention_reason = getAttentionReason(enriched)

      return enriched
    })

    // Step 6: Final tab filtering (post-enrichment for sentiment/wait-based categories)
    if (tab) {
      enrichedData = enrichedData.filter((conv) => categorizeConversation(conv) === tab)
    }

    // Step 7: Paginate
    const total = enrichedData.length
    const pages = Math.ceil(total / perPage)
    const from = (page - 1) * perPage
    const paginatedData = enrichedData.slice(from, from + perPage)

    return NextResponse.json({
      data: paginatedData,
      total,
      pages,
    })
  } catch (error) {
    console.error('Erro ao buscar conversas:', error)
    return NextResponse.json({ data: [], total: 0, pages: 0 })
  }
}
