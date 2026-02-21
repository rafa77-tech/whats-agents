/**
 * API: POST /api/dashboard/meta/quality/kill-switch
 * Sprint 69 - Kill switch action for a Meta chip
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { chip_id } = body

    if (!chip_id) {
      return NextResponse.json({ error: 'chip_id required' }, { status: 400 })
    }

    const supabase = await createClient()

    const { error } = await supabase
      .from('julia_chips')
      .update({ status: 'paused', meta_quality_rating: 'RED' })
      .eq('id', chip_id)

    if (error) throw error

    return NextResponse.json({ status: 'ok', message: 'Kill switch activated' })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/quality/kill-switch:', error)
    return NextResponse.json({ error: 'Failed to activate kill switch' }, { status: 500 })
  }
}
