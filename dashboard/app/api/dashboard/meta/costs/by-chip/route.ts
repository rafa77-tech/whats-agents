/**
 * API: GET /api/dashboard/meta/costs/by-chip
 * Sprint 69 - Cost aggregated by chip
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const since = new Date()
    since.setDate(since.getDate() - 7)

    const supabase = await createClient()

    const { data, error } = await supabase
      .from('meta_conversation_costs')
      .select('chip_id, cost_usd')
      .gte('created_at', since.toISOString())

    if (error) throw error

    const items = data || []
    const grouped: Record<string, { total_messages: number; total_cost_usd: number }> = {}

    for (const item of items) {
      const cid = item.chip_id || 'unknown'
      if (!grouped[cid]) grouped[cid] = { total_messages: 0, total_cost_usd: 0 }
      grouped[cid].total_messages++
      grouped[cid].total_cost_usd += parseFloat(String(item.cost_usd || '0'))
    }

    const result = Object.entries(grouped).map(([chip_id, stats]) => ({
      chip_id,
      ...stats,
    }))

    return NextResponse.json({ status: 'ok', data: result })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/costs/by-chip:', error)
    return NextResponse.json({ error: 'Failed to fetch costs by chip' }, { status: 500 })
  }
}
