/**
 * API: GET /api/dashboard/meta/mm-lite
 * Sprint 71 — MM Lite metrics
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    const since = new Date()
    since.setDate(since.getDate() - 7)

    const { data, error } = await supabase
      .from('meta_mm_lite_metrics')
      .select('delivery_status, sent_at')
      .gte('sent_at', since.toISOString())

    if (error) throw error

    const rows = data || []
    const total = rows.length
    const delivered = rows.filter(
      (r) => r.delivery_status === 'delivered' || r.delivery_status === 'read'
    ).length
    const read = rows.filter((r) => r.delivery_status === 'read').length

    const metrics = {
      total_sent: total,
      delivered,
      read,
      delivery_rate: total > 0 ? Math.round((delivered / total) * 10000) / 10000 : 0,
      read_rate: total > 0 ? Math.round((read / total) * 10000) / 10000 : 0,
      enabled: process.env.META_MM_LITE_ENABLED === 'true',
    }

    return NextResponse.json({ status: 'ok', data: metrics })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/mm-lite:', error)
    return NextResponse.json({ error: 'Failed to fetch MM Lite metrics' }, { status: 500 })
  }
}
