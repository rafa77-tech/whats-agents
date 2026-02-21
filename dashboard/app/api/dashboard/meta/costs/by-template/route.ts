/**
 * API: GET /api/dashboard/meta/costs/by-template
 * Sprint 69 - Cost aggregated by template
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
      .select('template_name, message_category, cost_usd')
      .gte('created_at', since.toISOString())
      .not('template_name', 'is', null)

    if (error) throw error

    const items = data || []
    const grouped: Record<
      string,
      { category: string; total_sent: number; total_cost_usd: number }
    > = {}

    for (const item of items) {
      const name = item.template_name || 'unknown'
      if (!grouped[name]) {
        grouped[name] = {
          category: item.message_category || 'MARKETING',
          total_sent: 0,
          total_cost_usd: 0,
        }
      }
      grouped[name].total_sent++
      grouped[name].total_cost_usd += parseFloat(String(item.cost_usd || '0'))
    }

    const result = Object.entries(grouped).map(([template_name, stats]) => ({
      template_name,
      ...stats,
    }))

    return NextResponse.json({ status: 'ok', data: result })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/costs/by-template:', error)
    return NextResponse.json({ error: 'Failed to fetch costs by template' }, { status: 500 })
  }
}
