/**
 * API: GET /api/conversas/counts
 *
 * Retorna contadores por tab de supervisao.
 * Sprint 64: Real counts (no more 30% guessing)
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import type { TabCounts } from '@/types/conversas'

export const dynamic = 'force-dynamic'

const TWO_DAYS_MS = 48 * 60 * 60 * 1000
const ONE_HOUR_MS = 60 * 60 * 1000

export async function GET(request: NextRequest): Promise<NextResponse> {
  try {
    const searchParams = request.nextUrl.searchParams
    const chipId = searchParams.get('chip_id')

    const supabase = createAdminClient()

    // If filtering by chip, get conversation IDs first
    let conversationFilter: string[] | null = null

    if (chipId) {
      const { data: chipConversations } = await supabase
        .from('conversation_chips')
        .select('conversa_id')
        .eq('chip_id', chipId)
        .eq('active', true)

      conversationFilter = chipConversations?.map((cc) => cc.conversa_id) || []

      if (conversationFilter.length === 0) {
        const emptyCounts: TabCounts = {
          atencao: 0,
          julia_ativa: 0,
          aguardando: 0,
          encerradas: 0,
        }
        return NextResponse.json(emptyCounts)
      }
    }

    const twoDaysAgo = new Date(Date.now() - TWO_DAYS_MS).toISOString()

    // Try RPC first
    const { data, error } = await supabase.rpc('get_supervision_tab_counts', {
      chip_conv_ids: conversationFilter,
      two_days_ago: twoDaysAgo,
    })

    if (!error && data) {
      return NextResponse.json(data)
    }

    // Fallback: compute real counts
    console.warn('RPC get_supervision_tab_counts not available, using fallback')
    const counts = await computeRealCounts(supabase, conversationFilter, twoDaysAgo)
    return NextResponse.json(counts)
  } catch (error) {
    console.error('Erro ao buscar contadores:', error)
    const emptyCounts: TabCounts = {
      atencao: 0,
      julia_ativa: 0,
      aguardando: 0,
      encerradas: 0,
    }
    return NextResponse.json(emptyCounts)
  }
}

async function computeRealCounts(
  supabase: ReturnType<typeof createAdminClient>,
  conversationFilter: string[] | null,
  twoDaysAgo: string
): Promise<TabCounts> {
  // Fetch active conversations with their last message direction
  let activeQuery = supabase
    .from('conversations')
    .select('id, status, controlled_by, last_message_at')
    .not('status', 'in', '("completed","archived","encerrada","arquivada")')

  if (conversationFilter) {
    activeQuery = activeQuery.in('id', conversationFilter)
  }

  const { data: activeConversations } = await activeQuery.limit(1000)

  // Fetch last message direction for active conversations
  const activeIds = (activeConversations || []).map((c) => c.id)

  const lastMsgDirectionMap = new Map<string, 'entrada' | 'saida'>()

  if (activeIds.length > 0) {
    const { data: lastMessages } = await supabase.rpc('get_last_messages', {
      conv_ids: activeIds,
    })

    lastMessages?.forEach((msg: { conversation_id: string; autor_tipo: string | null }) => {
      lastMsgDirectionMap.set(
        msg.conversation_id,
        msg.autor_tipo === 'medico' ? 'entrada' : 'saida'
      )
    })
  }

  // Fetch active handoffs
  const { data: handoffs } = await supabase
    .from('handoffs')
    .select('conversation_id')
    .in('conversation_id', activeIds.length > 0 ? activeIds : ['__none__'])
    .eq('status', 'pendente')

  const handoffSet = new Set(handoffs?.map((h) => h.conversation_id) || [])

  // Categorize each conversation
  const counts: TabCounts = { atencao: 0, julia_ativa: 0, aguardando: 0, encerradas: 0 }

  for (const conv of activeConversations || []) {
    const lastMsgDirection = lastMsgDirectionMap.get(conv.id) || null
    const hasHandoff = handoffSet.has(conv.id)

    // Atencao: handoff, human-controlled, or waiting > 1h with last msg from doctor
    if (conv.controlled_by === 'human' || hasHandoff) {
      counts.atencao++
      continue
    }

    if (lastMsgDirection === 'entrada' && conv.last_message_at) {
      const waitMs = Date.now() - new Date(conv.last_message_at).getTime()
      if (waitMs > ONE_HOUR_MS) {
        counts.atencao++
        continue
      }
    }

    // Aguardando: AI, last msg is outgoing (Julia sent, waiting for doctor)
    if (lastMsgDirection === 'saida' && conv.controlled_by === 'ai') {
      counts.aguardando++
      continue
    }

    // Julia ativa: AI active, doctor engaged
    counts.julia_ativa++
  }

  // Count encerradas separately (last 48h)
  let encerradasQuery = supabase
    .from('conversations')
    .select('id', { count: 'exact', head: true })
    .in('status', ['completed', 'archived'])
    .gte('updated_at', twoDaysAgo)

  if (conversationFilter) {
    encerradasQuery = encerradasQuery.in('id', conversationFilter)
  }

  const { count: encerradasCount } = await encerradasQuery
  counts.encerradas = encerradasCount || 0

  return counts
}
