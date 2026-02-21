/**
 * API: GET /api/dashboard/meta/quality
 * Sprint 69 - Quality overview for all Meta chips
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    const { data: chips, error } = await supabase
      .from('chips')
      .select('id, instance_name, status, meta_waba_id, meta_quality_rating, trust_score')
      .not('meta_waba_id', 'is', null)

    if (error) throw error

    const items = chips || []
    const overview = {
      total: items.length,
      green: items.filter((c) => c.meta_quality_rating === 'GREEN').length,
      yellow: items.filter((c) => c.meta_quality_rating === 'YELLOW').length,
      red: items.filter((c) => c.meta_quality_rating === 'RED').length,
      unknown: items.filter((c) => !c.meta_quality_rating || c.meta_quality_rating === 'UNKNOWN')
        .length,
      chips: items.map((c) => ({
        chip_id: c.id,
        chip_nome: c.instance_name,
        waba_id: c.meta_waba_id,
        quality_rating: c.meta_quality_rating || 'UNKNOWN',
        trust_score: c.trust_score || 0,
        status: c.status,
      })),
    }

    return NextResponse.json({ status: 'ok', data: overview })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/quality:', error)
    return NextResponse.json({ error: 'Failed to fetch quality data' }, { status: 500 })
  }
}
