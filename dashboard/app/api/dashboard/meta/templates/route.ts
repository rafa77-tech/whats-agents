/**
 * API: GET /api/dashboard/meta/templates
 * Sprint 69 - Meta templates with analytics
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    const { data, error } = await supabase
      .from('meta_templates')
      .select(
        'id, waba_id, template_name, category, status, language, quality_score, meta_template_id, components, variable_mapping, created_at, updated_at'
      )
      .order('created_at', { ascending: false })

    if (error) throw error

    return NextResponse.json({ status: 'ok', data: data || [] })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/templates:', error)
    return NextResponse.json({ error: 'Failed to fetch templates' }, { status: 500 })
  }
}
