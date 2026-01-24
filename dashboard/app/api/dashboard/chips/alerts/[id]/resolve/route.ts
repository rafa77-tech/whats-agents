/**
 * API: POST /api/dashboard/chips/alerts/[id]/resolve
 *
 * Marca um alerta como resolvido.
 */

import { NextRequest, NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const supabase = await createClient()
    const { id } = await params
    const body = await request.json()
    const { notes } = body

    const { error } = await supabase
      .from('chip_alerts')
      .update({
        resolved: true,
        resolved_at: new Date().toISOString(),
        resolved_by: 'dashboard_user',
        acao_tomada: notes || 'Resolvido via dashboard',
      })
      .eq('id', id)

    if (error) throw error

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Error resolving alert:', error)
    return NextResponse.json({ error: 'Failed to resolve alert' }, { status: 500 })
  }
}
