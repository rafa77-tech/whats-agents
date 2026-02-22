/**
 * API: GET /api/dashboard/meta/windows
 * Sprint 71 — Active/expiring/expired conversation windows
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()
    const now = new Date().toISOString()

    // 4 hours from now
    const soonExpiry = new Date()
    soonExpiry.setHours(soonExpiry.getHours() + 4)

    const { data, error } = await supabase
      .from('meta_conversation_windows')
      .select('chip_id, telefone, window_type, expires_at')
      .order('expires_at', { ascending: true })

    if (error) throw error

    const rows = data || []

    const active = rows.filter((r) => r.expires_at > now && r.expires_at > soonExpiry.toISOString())
    const expiring = rows.filter(
      (r) => r.expires_at > now && r.expires_at <= soonExpiry.toISOString()
    )
    const expired = rows.filter((r) => r.expires_at <= now)

    return NextResponse.json({
      status: 'ok',
      data: {
        active: active.length,
        expiring: expiring.length,
        expired: expired.length,
        total: rows.length,
        expiring_windows: expiring.slice(0, 20),
      },
    })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/windows:', error)
    return NextResponse.json({ error: 'Failed to fetch window data' }, { status: 500 })
  }
}
