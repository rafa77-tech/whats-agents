/**
 * API: GET /api/chips
 *
 * Lista chips disponíveis para filtro de inbox.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createAdminClient } from '@/lib/supabase/admin'

export const dynamic = 'force-dynamic'

export async function GET(_request: NextRequest) {
  try {
    const supabase = createAdminClient()

    // Get all active chips with conversation counts
    const { data: chips, error } = await supabase
      .from('chips')
      .select(
        `
        id,
        telefone,
        instance_name,
        status,
        trust_level,
        pode_prospectar,
        msgs_enviadas_hoje,
        msgs_recebidas_hoje
      `
      )
      .in('status', ['active', 'warming', 'ready'])
      .order('instance_name', { ascending: true })

    if (error) {
      console.error('Erro ao buscar chips:', error)
      throw error
    }

    // Get conversation counts per chip
    const chipIds = (chips || []).map((c) => c.id)

    const { data: conversationCounts } = await supabase
      .from('conversation_chips')
      .select('chip_id')
      .in('chip_id', chipIds)
      .eq('active', true)

    // Count conversations per chip
    const countMap = new Map<string, number>()
    conversationCounts?.forEach((cc) => {
      countMap.set(cc.chip_id, (countMap.get(cc.chip_id) || 0) + 1)
    })

    // Transform data
    const data = (chips || []).map((chip) => ({
      id: chip.id,
      telefone: chip.telefone,
      instance_name: chip.instance_name,
      status: chip.status,
      trust_level: chip.trust_level,
      pode_prospectar: chip.pode_prospectar,
      msgs_enviadas_hoje: chip.msgs_enviadas_hoje || 0,
      msgs_recebidas_hoje: chip.msgs_recebidas_hoje || 0,
      conversation_count: countMap.get(chip.id) || 0,
    }))

    return NextResponse.json({ data })
  } catch (error) {
    console.error('Erro ao buscar chips:', error)
    return NextResponse.json({ data: [] })
  }
}
