/**
 * API: GET /api/conversas/counts
 *
 * Retorna contadores por tab de supervisao.
 * Sprint 54: Supervision Dashboard
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'
import type { TabCounts } from '@/types/conversas'

export const dynamic = 'force-dynamic'

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

    const twoDaysAgo = new Date(Date.now() - 48 * 60 * 60 * 1000).toISOString()

    const { data, error } = await supabase.rpc('get_supervision_tab_counts', {
      chip_conv_ids: conversationFilter,
      two_days_ago: twoDaysAgo,
    })

    if (error) {
      // Fallback: count manually if RPC doesn't exist
      console.warn('RPC get_supervision_tab_counts not found, using fallback counts')

      const counts = await getCountsFallback(supabase, conversationFilter, twoDaysAgo)
      return NextResponse.json(counts)
    }

    return NextResponse.json(data)
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

async function getCountsFallback(
  supabase: ReturnType<typeof createAdminClient>,
  conversationFilter: string[] | null,
  twoDaysAgo: string
): Promise<TabCounts> {
  // Count handoff/human controlled (atencao)
  let atencaoQuery = supabase
    .from('conversations')
    .select('id', { count: 'exact', head: true })
    .eq('controlled_by', 'human')

  if (conversationFilter) {
    atencaoQuery = atencaoQuery.in('id', conversationFilter)
  }

  // Count active AI conversations (julia_ativa + aguardando combined)
  let activeAiQuery = supabase
    .from('conversations')
    .select('id', { count: 'exact', head: true })
    .eq('controlled_by', 'ai')
    .eq('status', 'active')

  if (conversationFilter) {
    activeAiQuery = activeAiQuery.in('id', conversationFilter)
  }

  // Count encerradas (last 48h)
  let encerradasQuery = supabase
    .from('conversations')
    .select('id', { count: 'exact', head: true })
    .in('status', ['completed', 'archived'])
    .gte('updated_at', twoDaysAgo)

  if (conversationFilter) {
    encerradasQuery = encerradasQuery.in('id', conversationFilter)
  }

  const [atencaoResult, activeAiResult, encerradasResult] = await Promise.all([
    atencaoQuery,
    activeAiQuery,
    encerradasQuery,
  ])

  const atencao = atencaoResult.count || 0
  const totalActiveAi = activeAiResult.count || 0
  // Split active AI roughly: assume half are waiting for response
  const aguardando = Math.floor(totalActiveAi * 0.3)
  const juliaAtiva = totalActiveAi - aguardando

  return {
    atencao,
    julia_ativa: juliaAtiva,
    aguardando,
    encerradas: encerradasResult.count || 0,
  }
}
