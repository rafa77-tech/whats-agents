/**
 * API: GET /api/dashboard/meta/quality/history?chip_id=X
 * Sprint 69 - Quality history timeline for a chip
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  try {
    const chipId = request.nextUrl.searchParams.get('chip_id')
    if (!chipId) {
      return NextResponse.json({ error: 'chip_id required' }, { status: 400 })
    }

    const supabase = await createClient()

    const { data, error } = await supabase
      .from('meta_quality_history')
      .select('timestamp, quality_rating, trust_score')
      .eq('chip_id', chipId)
      .order('timestamp', { ascending: true })
      .limit(100)

    if (error) throw error

    return NextResponse.json({ status: 'ok', data: data || [] })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/quality/history:', error)
    return NextResponse.json({ error: 'Failed to fetch quality history' }, { status: 500 })
  }
}
