/**
 * API: GET /api/dashboard/meta/flows
 * Sprint 69 - List all WhatsApp Flows with response counts
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    const { data: flows, error } = await supabase
      .from('meta_flows')
      .select(
        'id, waba_id, meta_flow_id, name, flow_type, status, json_definition, created_at, updated_at'
      )
      .order('created_at', { ascending: false })

    if (error) throw error

    // Fetch response counts per flow
    const flowIds = (flows ?? []).map((f) => f.id)
    let responseCounts: Record<string, number> = {}

    if (flowIds.length > 0) {
      const { data: counts, error: countError } = await supabase
        .from('meta_flow_responses')
        .select('flow_id')
        .in('flow_id', flowIds)

      if (!countError && counts) {
        responseCounts = counts.reduce<Record<string, number>>((acc, row) => {
          const key = row.flow_id as string
          acc[key] = (acc[key] ?? 0) + 1
          return acc
        }, {})
      }
    }

    const enriched = (flows ?? []).map((f) => ({
      ...f,
      response_count: responseCounts[f.id] ?? 0,
    }))

    return NextResponse.json({ status: 'ok', data: enriched })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/flows:', error)
    return NextResponse.json({ error: 'Failed to fetch flows' }, { status: 500 })
  }
}
