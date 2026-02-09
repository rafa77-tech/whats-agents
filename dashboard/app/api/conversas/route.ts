/**
 * API: GET /api/conversas
 *
 * Lista conversas do banco de dados com informações do chip.
 * Sprint 54: Enrichment (sentimento, confidence, stage, handoff)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import type { SupervisionTab } from '@/types/conversas'

export const dynamic = 'force-dynamic'

function categorizeConversation(conv: {
  controlled_by: string
  status: string
  sentimento_score?: number | null | undefined
  last_message_direction?: string | null | undefined
  last_message_at?: string | null | undefined
  has_handoff?: boolean | undefined
}): SupervisionTab {
  // Atencao: handoff OR very negative sentiment OR waiting too long
  if (conv.controlled_by === 'human' || conv.has_handoff) return 'atencao'
  if (conv.sentimento_score != null && conv.sentimento_score <= -2) return 'atencao'

  if (conv.last_message_direction === 'entrada' && conv.last_message_at) {
    const waitMs = Date.now() - new Date(conv.last_message_at).getTime()
    if (waitMs > 60 * 60 * 1000) return 'atencao' // > 60 min
  }

  // Encerradas
  if (['completed', 'archived', 'encerrada', 'arquivada'].includes(conv.status)) {
    return 'encerradas'
  }

  // Aguardando: Julia sent last, waiting for doctor reply
  if (conv.last_message_direction === 'saida' && conv.controlled_by === 'ai') {
    return 'aguardando'
  }

  // Julia ativa: AI active
  return 'julia_ativa'
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

    // First, get conversation IDs filtered by chip if needed
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

    // Build main query with join to clientes
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

    // Filter by chip's conversation IDs
    if (conversationIds) {
      query = query.in('id', conversationIds)
    }

    // Apply search filter
    if (search) {
      query = query.or(
        `clientes.primeiro_nome.ilike.%${search}%,clientes.sobrenome.ilike.%${search}%,clientes.telefone.ilike.%${search}%`
      )
    }

    query = query.order('last_message_at', { ascending: false, nullsFirst: false }).limit(200)

    const { data: conversations, error } = await query

    if (error) {
      console.error('Erro ao buscar conversas:', error)
      throw error
    }

    // Get conversation IDs for enrichment
    const conversaIds = (conversations || []).map((c) => c.id)

    // Parallel enrichment queries
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

      // Last messages with direction
      supabase
        .from('interacoes')
        .select('conversation_id, conteudo, autor_tipo, created_at')
        .in('conversation_id', conversaIds)
        .order('created_at', { ascending: false }),

      // Active handoffs
      supabase
        .from('handoffs')
        .select('conversation_id, motivo, status')
        .in('conversation_id', conversaIds)
        .eq('status', 'pendente'),
    ])

    // Create maps
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

    const lastMessageMap = new Map<string, { conteudo: string; direction: 'entrada' | 'saida' }>()
    lastMessagesResult.data?.forEach((msg) => {
      if (!lastMessageMap.has(msg.conversation_id)) {
        lastMessageMap.set(msg.conversation_id, {
          conteudo: msg.conteudo || '',
          direction: msg.autor_tipo === 'medico' ? 'entrada' : 'saida',
        })
      }
    })

    const handoffMap = new Map<string, string>()
    handoffsResult.data?.forEach((h) => {
      handoffMap.set(h.conversation_id, h.motivo || 'Handoff pendente')
    })

    // Transform data with enrichment
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

      return {
        id: c.id,
        cliente_nome: clienteNome,
        cliente_telefone: cliente?.telefone || '',
        status: c.status || 'active',
        controlled_by: c.controlled_by || 'ai',
        last_message: lastMsg?.conteudo || undefined,
        last_message_at: c.last_message_at,
        last_message_direction: lastMsg?.direction || undefined,
        unread_count: 0,
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
        has_handoff: handoffMap.has(c.id),
        handoff_reason: handoffReason || undefined,
      }
    })

    // Apply tab filter after enrichment
    if (tab) {
      enrichedData = enrichedData.filter((conv) => {
        const category = categorizeConversation(conv)
        return category === tab
      })
    }

    // Apply pagination on filtered results
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
