/**
 * API: GET /api/dashboard/meta/costs/summary?period=7d
 * Sprint 69 - Cost summary for Meta messages
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const period = request.nextUrl.searchParams.get('period') || '7d'
    const days = period === '30d' ? 30 : period === '1d' ? 1 : 7

    const since = new Date()
    since.setDate(since.getDate() - days)

    const supabase = await createClient()

    const { data, error } = await supabase
      .from('meta_conversation_costs')
      .select('message_category, cost_usd, is_free')
      .gte('created_at', since.toISOString())

    if (error) throw error

    const items = data || []
    const freeCount = items.filter((i) => i.is_free).length
    const totalCost = items.reduce((sum, i) => sum + parseFloat(String(i.cost_usd || '0')), 0)

    const byCategory: Record<string, { count: number; cost: number }> = {}
    for (const item of items) {
      const cat = item.message_category || 'unknown'
      if (!byCategory[cat]) byCategory[cat] = { count: 0, cost: 0 }
      byCategory[cat].count++
      byCategory[cat].cost += parseFloat(String(item.cost_usd || '0'))
    }

    const summary = {
      total_messages: items.length,
      free_messages: freeCount,
      paid_messages: items.length - freeCount,
      total_cost_usd: totalCost,
      by_category: byCategory,
    }

    return NextResponse.json({ status: 'ok', data: summary })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/costs/summary:', error)
    return NextResponse.json({ error: 'Failed to fetch cost summary' }, { status: 500 })
  }
}
