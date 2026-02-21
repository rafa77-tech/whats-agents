/**
 * API: GET/DELETE /api/dashboard/meta/flows/[id]
 * Sprint 69 - Get flow detail / Deprecate flow
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

interface RouteParams {
  params: Promise<{ id: string }>
}

export async function GET(_request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params
    const supabase = await createClient()

    const { data: flow, error } = await supabase
      .from('meta_flows')
      .select(
        'id, waba_id, meta_flow_id, name, flow_type, status, json_definition, created_at, updated_at'
      )
      .eq('id', id)
      .single()

    if (error || !flow) {
      return NextResponse.json({ error: 'Flow not found' }, { status: 404 })
    }

    // Get response count
    const { count } = await supabase
      .from('meta_flow_responses')
      .select('id', { count: 'exact', head: true })
      .eq('flow_id', id)

    return NextResponse.json({
      status: 'ok',
      data: { ...flow, response_count: count ?? 0 },
    })
  } catch (error) {
    console.error('Error in GET /api/dashboard/meta/flows/[id]:', error)
    return NextResponse.json({ error: 'Failed to fetch flow' }, { status: 500 })
  }
}

export async function DELETE(_request: NextRequest, { params }: RouteParams) {
  try {
    const { id } = await params
    const supabase = await createClient()

    const { data: flow, error: fetchError } = await supabase
      .from('meta_flows')
      .select('id, status')
      .eq('id', id)
      .single()

    if (fetchError || !flow) {
      return NextResponse.json({ error: 'Flow not found' }, { status: 404 })
    }

    if (flow.status !== 'PUBLISHED') {
      return NextResponse.json({ error: 'Only PUBLISHED flows can be deprecated' }, { status: 400 })
    }

    const { error } = await supabase
      .from('meta_flows')
      .update({ status: 'DEPRECATED', updated_at: new Date().toISOString() })
      .eq('id', id)

    if (error) throw error

    return NextResponse.json({ status: 'ok', message: 'Flow deprecated' })
  } catch (error) {
    console.error('Error in DELETE /api/dashboard/meta/flows/[id]:', error)
    return NextResponse.json({ error: 'Failed to deprecate flow' }, { status: 500 })
  }
}
