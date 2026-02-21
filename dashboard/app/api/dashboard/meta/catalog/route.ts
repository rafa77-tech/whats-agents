/**
 * API: GET /api/dashboard/meta/catalog
 * Sprint 71 — Catalog products list
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    const { data, error } = await supabase
      .from('meta_catalog_products')
      .select('*')
      .order('updated_at', { ascending: false })
      .limit(100)

    if (error) throw error

    return NextResponse.json({ status: 'ok', data: data || [] })
  } catch (error) {
    console.error('Error in /api/dashboard/meta/catalog:', error)
    return NextResponse.json({ error: 'Failed to fetch catalog products' }, { status: 500 })
  }
}
