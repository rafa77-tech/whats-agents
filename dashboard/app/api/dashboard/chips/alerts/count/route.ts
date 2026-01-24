/**
 * API: GET /api/dashboard/chips/alerts/count
 *
 * Retorna contagem de alertas ativos.
 */

import { NextResponse } from 'next/server'
import { createClient } from '@/lib/supabase/server'

export const dynamic = 'force-dynamic'

export async function GET() {
  try {
    const supabase = await createClient()

    const { data: alerts, error } = await supabase
      .from('chip_alerts')
      .select('severity')
      .eq('resolved', false)

    if (error) throw error

    const total = alerts?.length || 0
    const critical = alerts?.filter((a) => a.severity === 'critico').length || 0
    const warning = alerts?.filter((a) => a.severity === 'alerta').length || 0

    return NextResponse.json({ total, critical, warning })
  } catch (error) {
    console.error('Error fetching alert count:', error)
    return NextResponse.json({ total: 0, critical: 0, warning: 0 })
  }
}
