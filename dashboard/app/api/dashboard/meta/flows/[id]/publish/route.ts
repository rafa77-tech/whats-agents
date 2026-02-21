/**
 * API: POST /api/dashboard/meta/flows/[id]/publish
 * Sprint 69 - Publish a draft flow
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

interface RouteParams {
  params: Promise<{ id: string }>
}

export async function POST(_request: NextRequest, { params }: RouteParams) {
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

    if (flow.status !== 'DRAFT') {
      return NextResponse.json({ error: 'Only DRAFT flows can be published' }, { status: 400 })
    }

    const { error } = await supabase
      .from('meta_flows')
      .update({ status: 'PUBLISHED', updated_at: new Date().toISOString() })
      .eq('id', id)

    if (error) throw error

    return NextResponse.json({ status: 'ok', message: 'Flow published' })
  } catch (error) {
    console.error('Error in POST /api/dashboard/meta/flows/[id]/publish:', error)
    return NextResponse.json({ error: 'Failed to publish flow' }, { status: 500 })
  }
}
